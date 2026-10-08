import ij.IJ;
import ij.ImagePlus;
import ij.Macro;
import ij.gui.DialogListener;
import ij.gui.GenericDialog;
import ij.gui.MultiLineLabel;
import ij.gui.NonBlockingGenericDialog;
import ij.gui.OvalRoi;
import ij.gui.Overlay;
import ij.gui.Roi;
import ij.gui.ShapeRoi;
import ij.measure.Calibration;
import ij.measure.ResultsTable;
import ij.plugin.PlugIn;
import ij.plugin.frame.RoiManager;
import ij.process.AutoThresholder;
import ij.process.ByteProcessor;
import ij.process.ImageProcessor;
import ij.process.LUT;

import java.awt.AWTEvent;
import java.awt.Color;
import java.awt.Component;
import java.awt.Rectangle;
import java.awt.TextField;
import java.awt.geom.Area;
import java.awt.geom.Ellipse2D;
import java.util.Vector;

/**
 * Foam Binary / Ring tool for ImageJ and Fiji.
 *
 * Converts an image to black and white with a live preview, lets the user
 * control how much of the image is black vs. white (threshold, target
 * black %, or Otsu), and restricts the measurement to a circle, a ring
 * (circle 1 minus circle 2), two added circles, or the overlap of two
 * circles. Reports black / white %, area, ring width and centre offset in
 * calibrated units, and can create a cropped binary result image.
 *
 * Convention: a pixel is BLACK when its gray value is below the
 * threshold, so a higher threshold means more black.
 *
 * Install: copy Foam_Binary_Ring.jar into ImageJ's plugins folder and
 * restart. The command appears under Plugins > Foam Tools.
 */
public class Foam_Binary_Ring implements PlugIn, DialogListener {

    static final String[] SHAPES = {
        "Whole image",
        "Circle",
        "Ring (circle 1 minus circle 2)",
        "Add (circle 1 + circle 2)",
        "Overlap (circle 1 and circle 2)",
    };

    static final int WHOLE = 0, CIRCLE = 1, RING = 2, ADD = 3, OVERLAP = 4;

    // Settings remembered between runs (like built-in ImageJ commands)
    private static int sThreshold = -1;
    private static boolean sUseTarget = false;
    private static double sTarget = 50;
    private static boolean sAuto = true;
    private static boolean sInvert = false;
    private static int sShape = WHOLE;
    private static boolean sResults = true;
    private static boolean sCreate = true;
    private static boolean sRoiManager = false;

    private ImagePlus source;
    private ByteProcessor gray;
    private ImagePlus preview;

    // Current settings
    private int threshold;
    private boolean useTarget, auto, invert;
    private double target;
    private int shapeIndex;
    private double[] c1 = new double[3];
    private double[] c2 = new double[3];
    private boolean addResults, createImage, addToManager;

    // Computed
    private int usedThreshold;
    private int[] histogram;
    private String histogramKey;

    private GenericDialog dialog;
    private MultiLineLabel resultsLabel;

    // -----------------------------------------------------------------
    // PlugIn
    // -----------------------------------------------------------------

    @Override
    public void run(String arg) {

        source = IJ.getImage();

        if (source == null) {
            return;
        }

        gray = source.getProcessor().convertToByteProcessor(true);

        int w = gray.getWidth(), h = gray.getHeight();

        // Circle 1 from an existing oval selection, else centred
        Roi roi = source.getRoi();

        if (roi != null && roi.getType() == Roi.OVAL) {
            c1 = circleFromRoi(roi);
        } else {
            c1 = new double[] {w / 2.0, h / 2.0, Math.min(w, h) / 2.0};
        }

        c2 = new double[] {c1[0], c1[1], c1[2] / 2};

        boolean macro = Macro.getOptions() != null;

        if (!macro) {
            preview = new ImagePlus("Binary preview - " + source.getTitle(), gray.duplicate());
            preview.setCalibration(source.getCalibration());
            preview.show();
        }

        if (sThreshold < 0) {
            sThreshold = otsu(gray.getHistogram());
        }

        dialog = macro ? new GenericDialog("Foam Binary / Ring")
                       : new NonBlockingGenericDialog("Foam Binary / Ring");

        buildDialog(dialog);

        if (!macro) {
            dialog.addDialogListener(this);
            readDialog(dialog);
            update();
        }

        dialog.showDialog();

        if (dialog.wasCanceled()) {
            closePreview();
            return;
        }

        readDialog(dialog);
        remember();

        Roi shape = buildShape(shapeIndex, c1, c2, w, h);

        if (shapeIndex != WHOLE && (shape == null || isEmpty(shape))) {
            closePreview();
            IJ.error("Foam Binary / Ring", "The selected shape does not overlap the image.");
            return;
        }

        computeThreshold(shape);

        if (addResults) {
            addToResults(shape);
        }

        if (addToManager && shape != null) {
            RoiManager manager = RoiManager.getInstance();
            if (manager == null) {
                manager = new RoiManager();
            }
            Roi copy = (Roi) shape.clone();
            copy.setName(SHAPES[shapeIndex]);
            manager.addRoi(copy);
        }

        closePreview();

        if (createImage) {
            ImagePlus result = createResult(shape);
            result.show();
        }
    }

    // -----------------------------------------------------------------
    // Dialog
    // -----------------------------------------------------------------

    private void buildDialog(GenericDialog gd) {

        gd.addMessage("Black / white amount (higher threshold = more black)");
        gd.addSlider("Threshold", 0, 255, sThreshold);
        gd.addCheckbox("Auto_threshold (Otsu)", sAuto);
        gd.addCheckbox("Use_target black %", sUseTarget);
        gd.addNumericField("Target_black %", sTarget, 1);
        gd.addCheckbox("Invert black / white", sInvert);

        gd.addMessage("Region: circle 1 = red, circle 2 = blue. Draw an oval on the\npreview with the Oval tool, then click a button below.");
        gd.addChoice("Shape", SHAPES, SHAPES[sShape]);

        gd.addNumericField("Circle_1_X (px)", c1[0], 1);
        gd.addNumericField("Circle_1_Y (px)", c1[1], 1);
        gd.addNumericField("Circle_1_radius (px)", c1[2], 1);
        gd.addNumericField("Circle_2_X (px)", c2[0], 1);
        gd.addNumericField("Circle_2_Y (px)", c2[1], 1);
        gd.addNumericField("Circle_2_radius (px)", c2[2], 1);

        if (gd instanceof NonBlockingGenericDialog) {
            gd.addButton("Circle 1 = current oval selection", e -> fromSelection(0));
            gd.addButton("Circle 2 = current oval selection", e -> fromSelection(3));
            gd.addButton("Center circle 2 on circle 1", e -> centerSecond());
        }

        gd.addMessage("Black: --\n \n \n \n ");
        resultsLabel = asLabel(gd.getMessage());

        gd.addCheckbox("Add_to_Results table", sResults);
        gd.addCheckbox("Create_cropped binary image", sCreate);
        gd.addCheckbox("Add_to_ROI Manager", sRoiManager);

        gd.addHelp("https://github.com/Zdoink/Foam-measuring-tool#imagej--fiji-plugin");
        gd.setOKLabel("Apply");
    }

    private static MultiLineLabel asLabel(Component c) {
        return c instanceof MultiLineLabel ? (MultiLineLabel) c : null;
    }

    private void readDialog(GenericDialog gd) {

        threshold = clamp((int) Math.round(gd.getNextNumber()), 0, 255);
        auto = gd.getNextBoolean();
        useTarget = gd.getNextBoolean();
        target = gd.getNextNumber();
        invert = gd.getNextBoolean();

        shapeIndex = gd.getNextChoiceIndex();

        c1 = new double[] {gd.getNextNumber(), gd.getNextNumber(), gd.getNextNumber()};
        c2 = new double[] {gd.getNextNumber(), gd.getNextNumber(), gd.getNextNumber()};

        addResults = gd.getNextBoolean();
        createImage = gd.getNextBoolean();
        addToManager = gd.getNextBoolean();
    }

    private void remember() {
        sThreshold = threshold;
        sAuto = auto;
        sUseTarget = useTarget;
        sTarget = target;
        sInvert = invert;
        sShape = shapeIndex;
        sResults = addResults;
        sCreate = createImage;
        sRoiManager = addToManager;
    }

    @Override
    public boolean dialogItemChanged(GenericDialog gd, AWTEvent e) {

        // Moving the threshold slider means "use this threshold": switch
        // off Auto and Target % so the slider visibly takes effect. (When
        // the plugin itself moves the slider to the automatic value, the
        // value already matches and nothing is switched off.)
        if (e != null && isThresholdControl(gd, e.getSource())
                && sliderValue(gd) != usedThreshold) {
            Vector<?> boxes = gd.getCheckboxes();
            ((java.awt.Checkbox) boxes.get(0)).setState(false);
            ((java.awt.Checkbox) boxes.get(1)).setState(false);
        }

        readDialog(gd);

        if (gd.invalidNumber()) {
            return false;
        }

        update();
        return true;
    }

    private static int sliderValue(GenericDialog gd) {
        TextField field = (TextField) gd.getNumericFields().get(0);
        try {
            return (int) Math.round(Double.parseDouble(field.getText().trim()));
        } catch (NumberFormatException ex) {
            return -1;
        }
    }

    /** Shows the automatic / target threshold on the slider. */
    private void syncSlider(int value) {
        if (dialog == null || dialog.getSliders() == null || dialog.getSliders().isEmpty()) {
            return;
        }
        java.awt.Scrollbar bar = (java.awt.Scrollbar) dialog.getSliders().get(0);
        if (bar.getValue() != value) {
            bar.setValue(value);
        }
        TextField field = (TextField) dialog.getNumericFields().get(0);
        String text = String.valueOf(value);
        if (!field.getText().trim().equals(text)) {
            field.setText(text);
        }
    }

    private static boolean isThresholdControl(GenericDialog gd, Object source) {
        Vector<?> sliders = gd.getSliders();
        Vector<?> fields = gd.getNumericFields();
        return (sliders != null && !sliders.isEmpty() && source == sliders.get(0))
            || (fields != null && !fields.isEmpty() && source == fields.get(0));
    }

    /** Copies the oval selection on the preview (or source) into circle fields. */
    private void fromSelection(int firstField) {

        Roi roi = preview != null ? preview.getRoi() : null;

        if (roi == null) {
            roi = source.getRoi();
        }

        if (roi == null || roi.getType() != Roi.OVAL) {
            IJ.showMessage("Foam Binary / Ring",
                "Draw a circle with the Oval tool on the preview image first\n"
                + "(hold Shift while dragging for a perfect circle).");
            return;
        }

        double[] c = circleFromRoi(roi);

        setNumber(firstField, c[0]);
        setNumber(firstField + 1, c[1]);
        setNumber(firstField + 2, c[2]);

        if (preview != null) {
            preview.deleteRoi();
        }

        // Selecting circle 1 on a whole-image run switches to Circle mode
        Vector<?> choices = dialog.getChoices();
        java.awt.Choice shape = (java.awt.Choice) choices.get(0);

        if (firstField == 0 && shape.getSelectedIndex() == WHOLE) {
            shape.select(CIRCLE);
        }
        if (firstField == 3 && shape.getSelectedIndex() <= CIRCLE) {
            shape.select(RING);
        }

        refreshFromDialog();
    }

    private void centerSecond() {
        setNumber(3, getNumber(0));
        setNumber(4, getNumber(1));
        refreshFromDialog();
    }

    /** Circle numeric field i (0..5), after the threshold and target fields. */
    private TextField circleField(int i) {
        // numeric fields: threshold(slider), target, c1x, c1y, c1r, c2x, c2y, c2r
        return (TextField) dialog.getNumericFields().get(2 + i);
    }

    private void setNumber(int i, double value) {
        circleField(i).setText(IJ.d2s(value, 1));
    }

    private double getNumber(int i) {
        try {
            return Double.parseDouble(circleField(i).getText().trim());
        } catch (NumberFormatException ex) {
            return 0;
        }
    }

    private void refreshFromDialog() {
        // Re-read every field from the start, as the dialog itself does
        dialog.resetCounters();
        dialogItemChanged(dialog, null);
    }

    // -----------------------------------------------------------------
    // Preview
    // -----------------------------------------------------------------

    private void update() {

        int w = gray.getWidth(), h = gray.getHeight();

        Roi shape = buildShape(shapeIndex, c1, c2, w, h);

        computeThreshold(shape);

        if (auto || useTarget) {
            syncSlider(usedThreshold);
        }

        if (preview != null) {
            // Binary look via a lookup table: no pixels are changed, so
            // dragging the slider stays fast on large images
            preview.getProcessor().setLut(binaryLut(usedThreshold, invert));
            preview.setOverlay(overlayFor(shape, shapeIndex, c1, c2, w, h));
            preview.updateAndDraw();
        }

        if (resultsLabel != null) {
            resultsLabel.setText(summary(shape));
        }
    }

    private void computeThreshold(Roi shape) {

        int[] hist = histogramFor(shape);

        if (useTarget) {
            double fraction = target / 100.0;
            // With invert on, black pixels are the ones at or above the threshold
            usedThreshold = thresholdForBlackFraction(hist, invert ? 1 - fraction : fraction);
        } else if (auto) {
            usedThreshold = otsu(hist);
        } else {
            usedThreshold = threshold;
        }
    }

    private int[] histogramFor(Roi shape) {

        String key = shapeIndex == WHOLE || shape == null
            ? "whole"
            : shapeIndex + ":" + java.util.Arrays.toString(c1) + java.util.Arrays.toString(c2);

        if (!key.equals(histogramKey)) {
            if (key.equals("whole")) {
                gray.resetRoi();
            } else {
                gray.setRoi(shape);
            }
            histogram = gray.getHistogram();
            gray.resetRoi();
            histogramKey = key;
        }

        return histogram;
    }

    static final Color CIRCLE_1 = new Color(255, 60, 60);
    static final Color CIRCLE_2 = new Color(0, 200, 255);

    private static Overlay overlayFor(Roi shape, int shapeIndex, double[] c1, double[] c2, int w, int h) {

        Overlay overlay = new Overlay();

        if (shape == null) {
            return overlay;
        }

        // Dim everything outside the region
        Area rest = new Area(new Rectangle(0, 0, w, h));
        rest.subtract(shapeArea(shapeIndex, c1, c2));
        ShapeRoi outside = new ShapeRoi(rest);
        outside.setFillColor(new Color(0, 0, 0, 140));
        overlay.add(outside);

        // Outline circle 1 in red and, for two-circle shapes, circle 2 in blue
        Roi first = circleRoi(c1);
        first.setStrokeColor(CIRCLE_1);
        first.setStrokeWidth(2);
        overlay.add(first);

        if (shapeIndex >= RING) {
            Roi second = circleRoi(c2);
            second.setStrokeColor(CIRCLE_2);
            second.setStrokeWidth(2);
            overlay.add(second);
        }

        return overlay;
    }

    private String summary(Roi shape) {

        if (shapeIndex != WHOLE && (shape == null || isEmpty(shape))) {
            return "The selected shape does not overlap the image.\n \n \n \n ";
        }

        int[] hist = histogramFor(shape);
        double black = 100 * blackFraction(hist, usedThreshold, invert);

        Calibration cal = source.getCalibration();
        String unit = cal.getUnit();
        boolean calibrated = cal.scaled();

        long pixels = 0;
        for (int v : hist) pixels += v;

        StringBuilder s = new StringBuilder();
        s.append(String.format("Black: %.1f %%   White: %.1f %%   (threshold %d)%n",
            black, 100 - black, usedThreshold));

        String area = String.format("Area: %,d px²", pixels);
        if (calibrated) {
            area += String.format("  =  %s %s²",
                IJ.d2s(pixels * cal.pixelWidth * cal.pixelHeight, 2), unit);
        }
        s.append(area).append('\n');

        if (shapeIndex >= RING) {
            double width = Math.abs(c1[2] - c2[2]);
            double offset = Math.hypot(c2[0] - c1[0], c2[1] - c1[1]);
            if (shapeIndex == RING) {
                s.append("Ring width: ").append(withUnit(width, cal)).append('\n');
            }
            s.append("Center offset: ").append(withUnit(offset, cal)).append('\n');
        } else {
            s.append(" \n");
        }

        s.append(" ");
        return s.toString();
    }

    private static String withUnit(double px, Calibration cal) {
        String s = IJ.d2s(px, 1) + " px";
        if (cal.scaled()) {
            s += "  =  " + IJ.d2s(px * cal.pixelWidth, 2) + " " + cal.getUnit();
        }
        return s;
    }

    private void closePreview() {
        if (preview != null) {
            preview.changes = false;
            preview.close();
            preview = null;
        }
    }

    // -----------------------------------------------------------------
    // Output
    // -----------------------------------------------------------------

    private void addToResults(Roi shape) {

        int[] hist = histogramFor(shape);
        double black = 100 * blackFraction(hist, usedThreshold, invert);

        long pixels = 0;
        for (int v : hist) pixels += v;

        Calibration cal = source.getCalibration();

        ResultsTable rt = ResultsTable.getResultsTable();
        if (rt == null) {
            rt = new ResultsTable();
        }

        rt.incrementCounter();
        rt.addValue("Image", source.getTitle());
        rt.addValue("Shape", SHAPES[shapeIndex]);
        rt.addValue("Threshold", usedThreshold);
        rt.addValue("Black %", black);
        rt.addValue("White %", 100 - black);
        rt.addValue("Area (px)", pixels);
        rt.addValue("Area (" + cal.getUnit() + "^2)", pixels * cal.pixelWidth * cal.pixelHeight);

        if (shapeIndex != WHOLE) {
            rt.addValue("Radius 1 (" + cal.getUnit() + ")", c1[2] * cal.pixelWidth);
        }
        if (shapeIndex >= RING) {
            rt.addValue("Radius 2 (" + cal.getUnit() + ")", c2[2] * cal.pixelWidth);
            rt.addValue("Center offset (" + cal.getUnit() + ")",
                Math.hypot(c2[0] - c1[0], c2[1] - c1[1]) * cal.pixelWidth);
        }
        if (shapeIndex == RING) {
            rt.addValue("Ring width (" + cal.getUnit() + ")", Math.abs(c1[2] - c2[2]) * cal.pixelWidth);
        }

        rt.show("Results");
    }

    private ImagePlus createResult(Roi shape) {

        ByteProcessor binary = binarize(gray, usedThreshold, invert);
        String title = "Binary - " + source.getTitle();

        if (shape == null) {
            ImagePlus imp = new ImagePlus(title, binary);
            imp.setCalibration(source.getCalibration());
            return imp;
        }

        Rectangle b = shape.getBounds().intersection(new Rectangle(0, 0, gray.getWidth(), gray.getHeight()));

        binary.setRoi(b);
        ByteProcessor cropped = (ByteProcessor) binary.crop();

        // Paint everything outside the shape white
        Roi local = (Roi) shape.clone();
        local.setLocation(shape.getBounds().x - b.x, shape.getBounds().y - b.y);

        ByteProcessor outside = new ByteProcessor(b.width, b.height);
        outside.setColor(255);
        outside.fill();
        outside.setColor(0);
        outside.fill(local);

        byte[] px = (byte[]) cropped.getPixels();
        byte[] out = (byte[]) outside.getPixels();
        for (int i = 0; i < px.length; i++) {
            if (out[i] != 0) px[i] = (byte) 255;
        }

        ImagePlus imp = new ImagePlus(title, cropped);
        imp.setCalibration(source.getCalibration());
        imp.setRoi(local);
        return imp;
    }

    // -----------------------------------------------------------------
    // Image math (static so it can be tested without a GUI)
    // -----------------------------------------------------------------

    /** (cx, cy, r) of an oval selection; r averages width and height. */
    static double[] circleFromRoi(Roi roi) {
        Rectangle r = roi.getBounds();
        return new double[] {r.x + r.width / 2.0, r.y + r.height / 2.0, (r.width + r.height) / 4.0};
    }

    static OvalRoi circleRoi(double[] c) {
        return new OvalRoi(c[0] - c[2], c[1] - c[2], 2 * c[2], 2 * c[2]);
    }

    /** The selected region as a Roi, or null for the whole image. */
    static Roi buildShape(int shape, double[] c1, double[] c2, int w, int h) {

        if (shape == WHOLE) {
            return null;
        }

        if (shape == CIRCLE) {
            return circleRoi(c1);
        }

        return new ShapeRoi(shapeArea(shape, c1, c2));
    }

    /**
     * The region as exact geometry. Combining exact ellipses (rather than
     * ImageJ's oval polygons) keeps ring outlines free of a drawn "seam"
     * across the hole.
     */
    static Area shapeArea(int shape, double[] c1, double[] c2) {

        Area area = new Area(ellipse(c1));

        if (shape == CIRCLE) {
            return area;
        }

        Area second = new Area(ellipse(c2));

        switch (shape) {
            case RING:
                area.subtract(second);
                break;
            case ADD:
                area.add(second);
                break;
            case OVERLAP:
                area.intersect(second);
                break;
            default:
                throw new IllegalArgumentException("Unknown shape " + shape);
        }

        return area;
    }

    static Ellipse2D ellipse(double[] c) {
        return new Ellipse2D.Double(c[0] - c[2], c[1] - c[2], 2 * c[2], 2 * c[2]);
    }

    static boolean isEmpty(Roi roi) {
        Rectangle b = roi.getBounds();
        return b.width <= 0 || b.height <= 0;
    }

    /** Fraction of pixels that are black for a histogram and threshold. */
    static double blackFraction(int[] hist, int threshold, boolean invert) {
        long total = 0, below = 0;
        for (int i = 0; i < hist.length; i++) {
            total += hist[i];
            if (i < threshold) below += hist[i];
        }
        if (total == 0) return 0;
        double f = (double) below / total;
        return invert ? 1 - f : f;
    }

    /** Threshold giving a black fraction as close as possible to `fraction`. */
    static int thresholdForBlackFraction(int[] hist, double fraction) {
        fraction = Math.max(0, Math.min(1, fraction));

        long total = 0;
        for (int v : hist) total += v;
        if (total == 0) return 0;

        int best = 0;
        double bestError = Double.MAX_VALUE;
        long below = 0;

        // below = number of pixels with value < t, for t = 0..256
        for (int t = 0; t <= 256; t++) {
            double error = Math.abs((double) below / total - fraction);
            if (error < bestError) {
                bestError = error;
                best = t;
            }
            if (t < 256) below += hist[t];
        }

        return Math.min(best, 255);
    }

    /** Otsu threshold in this plugin's convention (black = value < threshold). */
    static int otsu(int[] hist) {
        long total = 0;
        for (int v : hist) total += v;
        if (total == 0) return 128;
        int level = new AutoThresholder().getThreshold(AutoThresholder.Method.Otsu, hist);
        // ImageJ's level is the last value of the dark class
        return clamp(level + 1, 0, 255);
    }

    static ByteProcessor binarize(ByteProcessor gray, int threshold, boolean invert) {
        ByteProcessor out = new ByteProcessor(gray.getWidth(), gray.getHeight());
        byte[] src = (byte[]) gray.getPixels();
        byte[] dst = (byte[]) out.getPixels();
        for (int i = 0; i < src.length; i++) {
            boolean black = (src[i] & 0xff) < threshold;
            if (invert) black = !black;
            dst[i] = black ? 0 : (byte) 255;
        }
        return out;
    }

    static LUT binaryLut(int threshold, boolean invert) {
        byte[] v = new byte[256];
        for (int i = 0; i < 256; i++) {
            boolean black = i < threshold;
            if (invert) black = !black;
            v[i] = black ? 0 : (byte) 255;
        }
        return new LUT(v, v, v);
    }

    static int clamp(int v, int lo, int hi) {
        return Math.max(lo, Math.min(hi, v));
    }
}
