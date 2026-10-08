import ij.gui.Roi;
import ij.process.ByteProcessor;

/**
 * Headless checks for Foam_Binary_Ring's image math.
 * Run: see imagej-plugin/README (javac + java with ij.jar on the classpath).
 */
public class TestFoamBinaryRing {

    static int failures = 0;

    static void check(boolean ok, String what) {
        System.out.println((ok ? "PASS  " : "FAIL  ") + what);
        if (!ok) failures++;
    }

    static boolean near(double a, double b, double tol) {
        return Math.abs(a - b) <= tol;
    }

    static int[] gradientHistogram() {
        int[] h = new int[256];
        java.util.Arrays.fill(h, 1);   // every gray value once
        return h;
    }

    static long count(int[] h) {
        long n = 0;
        for (int v : h) n += v;
        return n;
    }

    public static void main(String[] args) {

        int[] g = gradientHistogram();

        check(Foam_Binary_Ring.blackFraction(g, 0, false) == 0, "threshold 0 -> no black");
        check(Foam_Binary_Ring.blackFraction(g, 128, false) == 0.5, "threshold 128 -> 50% black");
        check(Foam_Binary_Ring.blackFraction(g, 64, true) == 0.75, "invert swaps black and white");

        for (double target : new double[] {0, 0.1, 0.25, 0.5, 0.9}) {
            int t = Foam_Binary_Ring.thresholdForBlackFraction(g, target);
            check(near(Foam_Binary_Ring.blackFraction(g, t, false), target, 1.0 / 256),
                "target " + target + " -> threshold " + t);
        }

        int[] twoLevels = new int[256];
        twoLevels[0] = 50;
        twoLevels[200] = 50;
        int otsu = Foam_Binary_Ring.otsu(twoLevels);
        check(Foam_Binary_Ring.blackFraction(twoLevels, otsu, false) == 0.5, "Otsu splits two levels (t=" + otsu + ")");

        // Ring area and histogram restricted to the ring
        ByteProcessor img = new ByteProcessor(200, 200);
        img.setColor(255);
        img.fill();
        img.setColor(0);
        img.fill(new Roi(90, 90, 20, 20));   // black square in the hole

        double[] outer = {100, 100, 80}, inner = {100, 100, 40};
        Roi ring = Foam_Binary_Ring.buildShape(Foam_Binary_Ring.RING, outer, inner, 200, 200);

        img.setRoi(ring);
        int[] ringHist = img.getHistogram();
        img.resetRoi();

        double expected = Math.PI * (80 * 80 - 40 * 40);
        check(near(count(ringHist), expected, expected * 0.02), "ring area " + count(ringHist) + " ~ " + Math.round(expected));
        check(Foam_Binary_Ring.blackFraction(ringHist, 128, false) == 0, "black square in the hole is not counted");
        check(Foam_Binary_Ring.blackFraction(img.getHistogram(), 128, false) > 0, "but it is counted for the whole image");

        // Add and overlap
        double[] a = {70, 50, 40}, b = {130, 50, 40};
        ByteProcessor canvas = new ByteProcessor(200, 100);
        long single = areaOf(canvas, Foam_Binary_Ring.buildShape(Foam_Binary_Ring.CIRCLE, a, b, 200, 100));
        long union = areaOf(canvas, Foam_Binary_Ring.buildShape(Foam_Binary_Ring.ADD, a, b, 200, 100));
        long lens = areaOf(canvas, Foam_Binary_Ring.buildShape(Foam_Binary_Ring.OVERLAP, a, b, 200, 100));
        check(near(union + lens, 2 * single, 2 * single * 0.01), "union + overlap = circle 1 + circle 2");
        check(lens > 0 && lens < single, "overlap is a lens smaller than one circle");

        // Shape partly outside the image is clipped, not an error
        Roi edge = Foam_Binary_Ring.buildShape(Foam_Binary_Ring.CIRCLE, new double[] {0, 0, 50}, b, 200, 100);
        long quarter = areaOf(canvas, edge);
        check(near(quarter, Math.PI * 2500 / 4, 120), "circle at the corner is clipped to a quarter (" + quarter + ")");

        // Binarize and LUT agree
        ByteProcessor ramp = new ByteProcessor(256, 1);
        for (int i = 0; i < 256; i++) ramp.set(i, 0, i);
        ByteProcessor bin = Foam_Binary_Ring.binarize(ramp, 100, false);
        check(bin.get(99, 0) == 0 && bin.get(100, 0) == 255, "binarize: value < threshold is black");

        double[] fromRoi = Foam_Binary_Ring.circleFromRoi(new ij.gui.OvalRoi(10, 20, 100, 100));
        check(fromRoi[0] == 60 && fromRoi[1] == 70 && fromRoi[2] == 50, "circle from oval selection");

        System.out.println(failures == 0 ? "\nAll checks passed" : "\n" + failures + " check(s) FAILED");
        System.exit(failures == 0 ? 0 : 1);
    }

    static long areaOf(ByteProcessor ip, Roi roi) {
        ip.setRoi(roi);
        long n = count(ip.getHistogram());
        ip.resetRoi();
        return n;
    }
}
