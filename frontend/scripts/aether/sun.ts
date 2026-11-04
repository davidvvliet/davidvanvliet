// The Sun's direction from the Moon (body-fixed frame) at a Julian date, for terrain.py's shadows.
import { skyAt } from "../../app/models/aether/sky";
console.log(JSON.stringify(skyAt(Number(process.argv[2])).sun.toArray()));
