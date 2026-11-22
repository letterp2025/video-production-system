// Editable EffectCraft build for the low-contrast red print texture.
var helperPath = new File($.fileName).parent.fsName + "/effectcraft_helpers.jsx";
$.evalFile(helperPath);

var C = {
    name: "11K FIRE Dotted Print Field",
    width: 1920,
    height: 1080,
    red: [225 / 255, 58 / 255, 46 / 255],
    white: [1, 1, 1],
    columns: 30,
    rows: 18,
    pitch: 24,
    diameter: 4,
    left: 600,
    top: 320,
};
var comp = VisualElementBuild.composition(C.name, C.width, C.height, 30, 1, C.white);
var cells = [];

for (var row = 0; row < C.rows; row++) {
    for (var column = 0; column < C.columns; column++) {
        cells.push({
            left: C.left + column * C.pitch,
            top: C.top + row * C.pitch,
            diameter: C.diameter,
        });
    }
}
VisualElementBuild.circles(comp, "540 Dot Vector Field", cells, C.red, 22);

writeLn("Built " + (C.columns * C.rows) + " low-opacity red print dots.");
