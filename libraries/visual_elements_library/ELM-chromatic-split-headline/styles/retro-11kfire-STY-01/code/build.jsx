// Build an isolated, editable version of the 11K FIRE homepage headline.
// Big Shoulders is read from EFFECTCRAFT_FONT_DIRS; this script does not copy fonts.

var CONFIG = {
    compositionName: "11K FIRE Chromatic Split Headline",
    width: 1920,
    height: 1080,
    fps: 30,
    duration: 1,
    font: "Big Shoulders",
    fontStyle: "ExtraBold",
    fontSize: 206,
    tracking: -55,
    ink: [24 / 255, 24 / 255, 24 / 255],
    red: [225 / 255, 58 / 255, 46 / 255],
    cyan: [41 / 255, 170 / 255, 207 / 255],
    paper: [1, 1, 1],
    firstPhrase: "POINT",
    secondPhrase: "OF VIEW.",
    left: 112,
    firstTop: 364,
    secondTop: 512,
    firstOffset: [-4, 2],
    secondOffset: [4, -2],
};

var comp = app.project.items.addComp(
    CONFIG.compositionName,
    CONFIG.width,
    CONFIG.height,
    1,
    CONFIG.duration,
    CONFIG.fps
);

comp.layers.addSolid(CONFIG.paper, "Paper", CONFIG.width, CONFIG.height, 1);

function addPhrase(name, value, color, left, top, offsetX, offsetY) {
    var document = new TextDocument(value);
    document.font = CONFIG.font;
    document.fontStyle = CONFIG.fontStyle;
    document.fontSize = CONFIG.fontSize;
    document.tracking = CONFIG.tracking;
    document.fillColor = color;

    var layer = comp.layers.addText(document);
    layer.name = name;

    // Align by the measured vector text bounds so the phrase starts at the
    // configured top-left even if the font's internal metrics change.
    var bounds = layer.sourceRectAtTime(0, false);
    layer.transform.position.setValue([
        left + offsetX - bounds.left,
        top + offsetY - bounds.top,
        0,
    ]);
    return layer;
}

// Offset copies sit behind the solid text; each phrase uses its own direction.
addPhrase("01 Point Cyan Offset", CONFIG.firstPhrase, CONFIG.cyan,
    CONFIG.left, CONFIG.firstTop, CONFIG.firstOffset[0], CONFIG.firstOffset[1]);
addPhrase("02 Point Ink", CONFIG.firstPhrase, CONFIG.ink,
    CONFIG.left, CONFIG.firstTop, 0, 0);
addPhrase("03 Of View Cyan Offset", CONFIG.secondPhrase, CONFIG.cyan,
    CONFIG.left, CONFIG.secondTop, CONFIG.secondOffset[0], CONFIG.secondOffset[1]);
addPhrase("04 Of View Red", CONFIG.secondPhrase, CONFIG.red,
    CONFIG.left, CONFIG.secondTop, 0, 0);

writeLn("Built editable " + CONFIG.compositionName + " at " + CONFIG.width + "x" + CONFIG.height + ".");
