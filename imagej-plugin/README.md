# Foam Binary / Ring: ImageJ / Fiji Plugin

The Binary / Circle Crop tool from the Foam Measuring Tool, packaged as a single-file plugin for **ImageJ** and **Fiji**.

- Live black-and-white preview with a **threshold slider**, **Target black %**, or **Auto (Otsu)** threshold
- **Invert** black and white
- Measure the **whole image**, a **circle**, a **ring** (circle 1 minus circle 2), two **added** circles, or the **overlap** of two circles
- Draw the circles with ImageJ's **Oval tool**, or type exact centers and radii
- Reports **black / white %**, **area**, **ring width** and **center offset**, in **µm** (or whatever unit is set) when the image has a scale
- Writes the results to ImageJ's **Results** table, can create a **cropped binary image**, and can add the shape to the **ROI Manager**
- **Macro recordable**, so you can batch-process many images

## Install

1. Download **[`Foam_Binary_Ring.jar`](Foam_Binary_Ring.jar)**.
2. Copy it into ImageJ's `plugins` folder:
   - **ImageJ:** `ImageJ/plugins/`
   - **Fiji:** `Fiji.app/plugins/`
3. Restart ImageJ / Fiji.

The command is **Plugins ▸ Foam Tools ▸ Foam Binary / Ring...**

Tested with ImageJ **1.54p**; any recent ImageJ 1.53+ or current Fiji should work. It runs on Java 8 and newer.

## Use

1. Open an image. Optionally set its scale with **Analyze ▸ Set Scale...** so results are in µm.
2. Optionally draw a circle on it with the **Oval tool** (hold **Shift** for a perfect circle). It becomes circle 1.
3. Run **Plugins ▸ Foam Tools ▸ Foam Binary / Ring...**. A **Binary preview** window opens next to the settings dialog.
4. Set the black / white amount:
   - Drag the **Threshold** slider (higher = more black), or
   - Tick **Use target black %** and type a percentage, or
   - Tick **Auto threshold (Otsu)**.
5. Choose a **Shape**. For a ring:
   1. Draw an oval around the outside edge on the preview, then click **Circle 1 = current oval selection**.
   2. Draw an oval around the hole, then click **Circle 2 = current oval selection**. The shape switches to Ring automatically.
   3. **Center circle 2 on circle 1** makes the ring concentric.
6. Read the results under the buttons, then click **Apply** to add them to the Results table and create the cropped image.

Circle 1 is outlined in **red** and circle 2 in **blue**, and everything outside the shape is dimmed. The slider, target % and Otsu settings only consider pixels inside the shape.

A pixel counts as **black** when its gray value is below the threshold. Color and 16-bit images are converted to 8-bit gray for the analysis; for stacks, the current slice is used.

## Macros and batch processing

Turn on **Plugins ▸ Macros ▸ Record...** and run the plugin to get the exact command. For example:

```javascript
run("Foam Binary / Ring...", "threshold=128 auto_threshold shape=[Ring (circle 1 minus circle 2)] circle_1_x=690 circle_1_y=535 circle_1_radius=447 circle_2_x=720 circle_2_y=555 circle_2_radius=208 add_to_results create_cropped");
```

Leave out a checkbox keyword to turn that option off (e.g. remove `create_cropped` to skip the cropped image).

## Results table columns

| Column | Meaning |
| ------ | ------- |
| Image, Shape | Source image and shape used |
| Threshold | Threshold applied (after Otsu / target %) |
| Black %, White % | Share of the shape's pixels that are black / white |
| Area (px), Area (unit^2) | Area of the shape in pixels and calibrated units |
| Radius 1, Radius 2 | Circle radii (calibrated) |
| Ring width | Radius 1 minus radius 2 (Ring only) |
| Center offset | Distance between the two circle centers |

## Building from source

You only need this to change the plugin. With a JDK installed:

```bash
./build.sh path/to/ij.jar        # ij.jar is in your ImageJ folder, or Fiji.app/jars/ij-*.jar
```

Run the tests:

```bash
javac -cp ij.jar:Foam_Binary_Ring.jar -d /tmp/test test/TestFoamBinaryRing.java
java -Djava.awt.headless=true -cp ij.jar:Foam_Binary_Ring.jar:/tmp/test TestFoamBinaryRing
```

(On Windows, use `;` instead of `:` between classpath entries.)
