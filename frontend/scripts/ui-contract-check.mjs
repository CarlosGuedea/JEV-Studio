import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
const home = read("pages/Home.tsx");
const canvas = read("components/CanvasArea.tsx");
const canvasStyles = read("components/CanvasArea.css");

assert.match(home, /flex-col[\s\S]*lg:flex-row/, "The editor layout must stack on small screens.");
assert.match(canvas, /min-w-0[\s\S]*lg:min-w-\[540px\]/, "The canvas must not force a desktop-width column on small screens.");
assert.match(canvas, /padding: 0\.1/, "The initial graph fit should prioritise readable nodes.");
assert.match(canvasStyles, /react-flow__minimap/, "React Flow minimap needs theme-aware styling.");
assert.match(canvasStyles, /react-flow__node-input/, "Custom input/output nodes must not inherit React Flow's white defaults.");

console.log("UI layout contracts pass.");
