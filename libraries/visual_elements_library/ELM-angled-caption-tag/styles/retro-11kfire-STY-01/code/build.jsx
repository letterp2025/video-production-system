// Editable EffectCraft build for the angled caption tag.
var helperPath = new File($.fileName).parent.fsName + "/effectcraft_helpers.jsx";
$.evalFile(helperPath);

var C = {
    name: "11K FIRE Angled Caption Tag",
    width: 1920,
    height: 1080,
    red: [225 / 255, 58 / 255, 46 / 255],
    white: [1, 1, 1],
};
var comp = VisualElementBuild.composition(C.name, C.width, C.height, 30, 1, C.white);

VisualElementBuild.rect(comp, "Caption Red Face", 586, 474, 748, 104, C.red, -3);
VisualElementBuild.text(comp, "Caption Text", "A POINT OF VIEW, IN MOTION", "Anton", "Regular", 44,
    C.white, 651, 503, { maxWidth: 618, tracking: 12, rotation: -3 });

writeLn("Built editable " + C.name + " at " + C.width + "x" + C.height + ".");
