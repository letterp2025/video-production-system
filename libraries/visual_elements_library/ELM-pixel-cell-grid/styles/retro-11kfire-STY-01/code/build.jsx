// Editable EffectCraft build of the empty 11K FIRE 27 x 27 pixel cell grid.
var helperPath = new File($.fileName).parent.fsName + "/effectcraft_helpers.jsx";
$.evalFile(helperPath);

var C = {
    name: "11K FIRE Pixel Cell Grid",
    width: 1920,
    height: 1080,
    rows: 27,
    columns: 27,
    paper: [1, 1, 1],
    cellSize: 13,
    stride: 18,
    origin: 7,
    scale: 1.6,
    left: 563,
    top: 112,
    gray: [
        [240 / 255, 241 / 255, 242 / 255],
        [227 / 255, 229 / 255, 231 / 255],
        [213 / 255, 216 / 255, 219 / 255],
        [199 / 255, 203 / 255, 207 / 255],
    ],
};
var comp = VisualElementBuild.composition(C.name, C.width, C.height, 30, 1, C.paper);
var cells = [];

for (var row = 0; row < C.rows; row++) {
    for (var column = 0; column < C.columns; column++) {
        var value = (column * 17 + row * 31 + column * row * 7) % 101;
        var shade = value < 7 ? 3 : value < 24 ? 2 : value < 57 ? 1 : 0;
        var fill = C.gray[shade];
        var left = C.left + (C.origin + column * C.stride) * C.scale;
        var top = C.top + (C.origin + row * C.stride) * C.scale;
        cells.push({
            left: left,
            top: top,
            width: C.cellSize * C.scale,
            height: C.cellSize * C.scale,
            color: fill,
        });
    }
}
VisualElementBuild.rectangles(comp, "27 x 27 Empty Pixel Cell Grid", cells);

writeLn("Built an empty 27 x 27 pixel cell grid with " + cells.length + " pale cells.");
