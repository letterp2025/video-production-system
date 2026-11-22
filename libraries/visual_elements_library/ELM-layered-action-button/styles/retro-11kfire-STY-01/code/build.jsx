// Editable EffectCraft build for the layered red call-to-action button.
var helperPath = new File($.fileName).parent.fsName + "/effectcraft_helpers.jsx";
$.evalFile(helperPath);

var C = {
    name: "11K FIRE Layered Action Button",
    width: 1920,
    height: 1080,
    ink: [24 / 255, 24 / 255, 24 / 255],
    red: [225 / 255, 58 / 255, 46 / 255],
    cyan: [41 / 255, 170 / 255, 207 / 255],
    white: [1, 1, 1],
};
var comp = VisualElementBuild.composition(C.name, C.width, C.height, 30, 1, C.white);

var x = 620, y = 428, width = 680, height = 154;
VisualElementBuild.rect(comp, "Cyan Hard Shadow", x + 13, y + 13, width, height, C.cyan);
VisualElementBuild.rect(comp, "Ink Hard Shadow", x + 7, y + 7, width, height, C.ink);
VisualElementBuild.rect(comp, "Red Button Face", x, y, width, height, C.red);
VisualElementBuild.text(comp, "Button Label", "SEE IT UNFOLD", "Anton", "Regular", 62, C.white,
    x + 46, y + 42, { maxWidth: 490, tracking: 8 });
VisualElementBuild.rect(comp, "Arrow Shaft", x + 564, y + 86, 66, 6, C.white, 45);
VisualElementBuild.rect(comp, "Arrow Head Horizontal", x + 590, y + 109, 30, 6, C.white);
VisualElementBuild.rect(comp, "Arrow Head Vertical", x + 617, y + 82, 6, 30, C.white);

writeLn("Built editable " + C.name + " at " + C.width + "x" + C.height + ".");
