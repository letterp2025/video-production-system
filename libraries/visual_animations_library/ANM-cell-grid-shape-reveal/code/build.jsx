// EffectCraft grid-shape reveal. Each cell is an individual shape layer.

var C = {
    name: "11K FIRE Cell-Grid Shape Reveal",
    targetMask: "flame",
    width: 1920,
    height: 1080,
    fps: 60,
    duration: 4,
    gridRows: 27,
    gridColumns: 27,
    cellSize: 13,
    stride: 18,
    origin: 7,
    scale: 1.6,
    left: 563,
    top: 112,
    pulseSampleFrames: 30, // 0.5 seconds at 60 fps
    activePalette: {
        dark: "#aa2119",
        light: "#f36a5c",
        accent: "#29aacf",
        main: "#e13a2e",
    },
    grayHex: ["#f0f1f2", "#e3e5e7", "#d5d8db", "#c7cbcf"],
};

var FPS = C.fps;
var DURATION_FRAMES = Math.round(C.duration * FPS);
var WHITE = [1, 1, 1];
var targetDataFile = new File(new File($.fileName).parent.fsName + "/target_masks.jsx");
$.evalFile(targetDataFile);
var maskRows = PIXEL_GRID_TARGETS[C.targetMask];
if (!maskRows) {
    throw new Error("Unknown target mask: " + C.targetMask);
}
if (maskRows.length !== C.gridRows) {
    throw new Error("Target mask must have exactly " + C.gridRows + " rows.");
}
for (var maskRow = 0; maskRow < maskRows.length; maskRow++) {
    if (maskRows[maskRow].length !== C.gridColumns) {
        throw new Error("Target mask row " + (maskRow + 1) + " must have " + C.gridColumns + " cells.");
    }
    for (var maskColumn = 0; maskColumn < maskRows[maskRow].length; maskColumn++) {
        var marker = maskRows[maskRow].charAt(maskColumn);
        if (marker !== "." && marker !== "#") {
            throw new Error("Target mask uses only '.' for empty and '#' for filled cells.");
        }
    }
}
var comp = app.project.items.addComp(C.name, C.width, C.height, 1, C.duration, FPS);
comp.layers.addSolid(WHITE, "White Background", C.width, C.height, 1);

function fromHex(hex) {
    return [
        parseInt(hex.substr(1, 2), 16) / 255,
        parseInt(hex.substr(3, 2), 16) / 255,
        parseInt(hex.substr(5, 2), 16) / 255,
    ];
}

function activeColor(value) {
    if (value < 7) return fromHex(C.activePalette.dark);
    if (value < 20) return fromHex(C.activePalette.light);
    if (value > 96) return fromHex(C.activePalette.accent);
    return fromHex(C.activePalette.main);
}

function grayColor(value) {
    var shade = value < 7 ? 3 : value < 24 ? 2 : value < 57 ? 1 : 0;
    return fromHex(C.grayHex[shade]);
}

function addCellLayer(name, left, top, size, color) {
    var layer = comp.layers.addShape();
    layer.name = name;
    var root = layer.property("ADBE Root Vectors Group");
    var group = root.addProperty("ADBE Vector Group");
    var vectors = group.property("ADBE Vectors Group");
    var rectangle = vectors.addProperty("ADBE Vector Shape - Rect");
    rectangle.property("ADBE Vector Rect Size").setValue([size, size]);
    rectangle.property("ADBE Vector Rect Position").setValue([size / 2, size / 2]);
    var fill = group.property("Contents").addProperty("ADBE Vector Graphic - Fill");
    var fillColor = fill.property("ADBE Vector Fill Color");
    fillColor.setValue(color);
    layer.transform.anchorPoint.setValue([size / 2, size / 2, 0]);
    layer.transform.position.setValue([left + size / 2, top + size / 2, 0]);
    return { layer: layer, fillColor: fillColor };
}

function setLinearKeyframes(property, keys) {
    for (var i = 0; i < keys.length; i++) {
        property.setValueAtTime(keys[i].frame / FPS, keys[i].value);
    }
    for (var j = 1; j <= keys.length; j++) {
        property.setInterpolationTypeAtKey(
            j,
            KeyframeInterpolationType.LINEAR,
            KeyframeInterpolationType.LINEAR
        );
    }
}

function pulseOpacity(elapsedMs, durationMs, startOffsetMs) {
    var cycleMs = durationMs * 2;
    var phaseMs = ((elapsedMs - startOffsetMs) % cycleMs + cycleMs) % cycleMs;
    var progress = phaseMs <= durationMs
        ? phaseMs / durationMs
        : 2 - phaseMs / durationMs;
    var eased = progress * progress * (3 - 2 * progress);
    return 0.62 + 0.38 * eased;
}

var cells = [];
var minSweep = Infinity;
var maxSweep = -Infinity;

for (var row = 0; row < C.gridRows; row++) {
    for (var column = 0; column < C.gridColumns; column++) {
        var value = (column * 17 + row * 31 + column * row * 7) % 101;
        var active = maskRows[row].charAt(column) === "#";
        var sweep = column - row;
        if (active) {
            minSweep = Math.min(minSweep, sweep);
            maxSweep = Math.max(maxSweep, sweep);
        }
        cells.push({
            row: row,
            column: column,
            value: value,
            active: active,
            sweep: sweep,
            left: C.left + (C.origin + column * C.stride) * C.scale,
            top: C.top + (C.origin + row * C.stride) * C.scale,
            size: C.cellSize * C.scale,
        });
    }
}

var activeCount = 0;
var pulseCount = 0;
var sweepRange = Math.max(1, maxSweep - minSweep);

for (var index = 0; index < cells.length; index++) {
    var cell = cells[index];
    var base = grayColor(cell.value);
    var result = addCellLayer(
        "Cell r" + (cell.row + 1) + " c" + (cell.column + 1) + (cell.active ? " Active" : " Field"),
        cell.left,
        cell.top,
        cell.size,
        base
    );

    if (cell.active) {
        activeCount++;
        var finalColor = activeColor(cell.value);
        var startMs = Math.round(((cell.sweep - minSweep) / sweepRange) * 260 + ((cell.column * 11 + cell.row * 13) % 20));
        var startFrame = Math.round(startMs * FPS / 1000);
        var durationMs = 60 + ((cell.column * 7 + cell.row * 11) % 25);
        var durationFrames = Math.max(3, Math.round(durationMs * FPS / 1000));
        var rotationKeys = [];

        // Match the source CSS rotateX turn, changing fill while the cell is edge-on.
        result.layer.threeDLayer = true;
        var xRotation = result.layer.transform.xRotation;
        for (var flipFrame = 0; flipFrame <= durationFrames; flipFrame++) {
            var progress = flipFrame / durationFrames;
            rotationKeys.push({
                frame: startFrame + flipFrame,
                value: progress <= 0.5 ? progress * 180 : (1 - progress) * 180,
            });
        }
        setLinearKeyframes(xRotation, rotationKeys);

        var midpointFrame = startFrame + Math.round(durationFrames / 2);
        result.fillColor.setValueAtTime(0, base);
        result.fillColor.setValueAtTime(midpointFrame / FPS, finalColor);
        result.fillColor.setInterpolationTypeAtKey(1, KeyframeInterpolationType.HOLD, KeyframeInterpolationType.HOLD);
        result.fillColor.setInterpolationTypeAtKey(2, KeyframeInterpolationType.HOLD, KeyframeInterpolationType.HOLD);
    } else {
        pulseCount++;
        var pulseDuration = 5200 + ((cell.column * 149 + cell.row * 307) % 4800);
        var pulseOffset = -((cell.column * 271 + cell.row * 593) % pulseDuration);
        var opacity = result.layer.transform.opacity;
        var opacityKeys = [];
        for (var frame = 0; frame <= DURATION_FRAMES; frame += C.pulseSampleFrames) {
            opacityKeys.push({
                frame: frame,
                value: 100 * pulseOpacity(frame * 1000 / FPS, pulseDuration, pulseOffset),
            });
        }
        if (opacityKeys[opacityKeys.length - 1].frame !== DURATION_FRAMES) {
            opacityKeys.push({
                frame: DURATION_FRAMES,
                value: 100 * pulseOpacity(C.duration * 1000, pulseDuration, pulseOffset),
            });
        }
        setLinearKeyframes(opacity, opacityKeys);
    }
}

writeLn("Built " + activeCount + " active cells from " + C.targetMask + " and " + pulseCount +
    " independently pulsing field cells at " + FPS + " fps for " + C.duration + " seconds.");
