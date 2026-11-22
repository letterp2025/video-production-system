// Small After Effects-style helpers shared by the EffectCraft element builders.
// Each build.jsx still owns its composition and visual settings.

var VisualElementBuild = (function () {
    function composition(name, width, height, fps, duration, paper) {
        var comp = app.project.items.addComp(name, width, height, 1, duration || 1, fps || 30);
        comp.layers.addSolid(paper || [1, 1, 1], "Paper", width, height, 1);
        return comp;
    }

    function rect(comp, name, left, top, width, height, color, rotation, opacity) {
        var layer = comp.layers.addShape();
        layer.name = name;
        var root = layer.property("ADBE Root Vectors Group");
        var group = root.addProperty("ADBE Vector Group");
        var contents = group.property("ADBE Vectors Group");
        var shape = contents.addProperty("ADBE Vector Shape - Rect");
        shape.property("ADBE Vector Rect Size").setValue([width, height]);
        shape.property("ADBE Vector Rect Position").setValue([width / 2, height / 2]);
        var fill = group.property("Contents").addProperty("ADBE Vector Graphic - Fill");
        fill.property("ADBE Vector Fill Color").setValue(color);
        layer.transform.anchorPoint.setValue([width / 2, height / 2, 0]);
        layer.transform.position.setValue([left + width / 2, top + height / 2, 0]);
        if (rotation) layer.transform.rotation.setValue(rotation);
        if (typeof opacity === "number") layer.transform.opacity.setValue(opacity);
        return layer;
    }

    function circle(comp, name, left, top, diameter, color, opacity) {
        var layer = comp.layers.addShape();
        layer.name = name;
        var root = layer.property("ADBE Root Vectors Group");
        var group = root.addProperty("ADBE Vector Group");
        var contents = group.property("ADBE Vectors Group");
        var shape = contents.addProperty("ADBE Vector Shape - Ellipse");
        shape.property("ADBE Vector Ellipse Size").setValue([diameter, diameter]);
        shape.property("ADBE Vector Ellipse Position").setValue([diameter / 2, diameter / 2]);
        var fill = group.property("Contents").addProperty("ADBE Vector Graphic - Fill");
        fill.property("ADBE Vector Fill Color").setValue(color);
        layer.transform.anchorPoint.setValue([0, 0, 0]);
        layer.transform.position.setValue([left, top, 0]);
        if (typeof opacity === "number") layer.transform.opacity.setValue(opacity);
        return layer;
    }

    function rectangles(comp, name, cells) {
        var layer = comp.layers.addShape();
        layer.name = name;
        layer.transform.anchorPoint.setValue([0, 0, 0]);
        layer.transform.position.setValue([0, 0, 0]);
        var root = layer.property("ADBE Root Vectors Group");
        var groups = {};
        var order = [];

        for (var i = 0; i < cells.length; i++) {
            var cell = cells[i];
            var key = cell.color.join(",");
            if (!groups[key]) {
                var group = root.addProperty("ADBE Vector Group");
                group.name = name + " Color " + (order.length + 1);
                groups[key] = { group: group, color: cell.color };
                order.push(key);
            }
            var vectors = groups[key].group.property("ADBE Vectors Group");
            var shape = vectors.addProperty("ADBE Vector Shape - Rect");
            shape.property("ADBE Vector Rect Size").setValue([cell.width, cell.height]);
            shape.property("ADBE Vector Rect Position").setValue([
                cell.left + cell.width / 2,
                cell.top + cell.height / 2,
            ]);
        }

        for (var j = 0; j < order.length; j++) {
            var entry = groups[order[j]];
            var fill = entry.group.property("Contents").addProperty("ADBE Vector Graphic - Fill");
            fill.property("ADBE Vector Fill Color").setValue(entry.color);
        }
        return layer;
    }

    function circles(comp, name, cells, color, opacity) {
        var layer = comp.layers.addShape();
        layer.name = name;
        layer.transform.anchorPoint.setValue([0, 0, 0]);
        layer.transform.position.setValue([0, 0, 0]);
        var root = layer.property("ADBE Root Vectors Group");
        var group = root.addProperty("ADBE Vector Group");
        group.name = name + " Vector Paths";
        var vectors = group.property("ADBE Vectors Group");

        for (var i = 0; i < cells.length; i++) {
            var cell = cells[i];
            var shape = vectors.addProperty("ADBE Vector Shape - Ellipse");
            shape.property("ADBE Vector Ellipse Size").setValue([cell.diameter, cell.diameter]);
            shape.property("ADBE Vector Ellipse Position").setValue([
                cell.left + cell.diameter / 2,
                cell.top + cell.diameter / 2,
            ]);
        }

        var fill = group.property("Contents").addProperty("ADBE Vector Graphic - Fill");
        fill.property("ADBE Vector Fill Color").setValue(color);
        if (typeof opacity === "number") layer.transform.opacity.setValue(opacity);
        return layer;
    }

    function text(comp, name, value, family, style, size, color, left, top, options) {
        options = options || {};
        var document = new TextDocument(value);
        document.font = family;
        document.fontStyle = style || "Regular";
        document.fontSize = size;
        document.fillColor = color;
        if (typeof options.tracking === "number") document.tracking = options.tracking;
        if (typeof options.leading === "number") document.leading = options.leading;
        var layer = comp.layers.addText(document);
        layer.name = name;
        var bounds = layer.sourceRectAtTime(0, false);
        var scale = options.maxWidth ? options.maxWidth / bounds.width : 1;
        layer.transform.scale.setValue([scale * 100, scale * 100, 100]);
        layer.transform.position.setValue([
            left - bounds.left * scale,
            top - bounds.top * scale,
            0,
        ]);
        if (options.rotation) layer.transform.rotation.setValue(options.rotation);
        if (typeof options.opacity === "number") layer.transform.opacity.setValue(options.opacity);
        return layer;
    }

    return {
        composition: composition,
        rect: rect,
        circle: circle,
        rectangles: rectangles,
        circles: circles,
        text: text,
    };
})();
