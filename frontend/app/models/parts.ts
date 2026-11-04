import * as THREE from "three";

// How a built model's meshes group into parts, shared by the models viewer and the Aether launch.

// Part family, as explode.py groups them: rtg_1 and rtg_1_fins -> rtg, feed_leg_3 -> feed_leg.
export const family = (name: string) => name.replace(/_fins$/, "").replace(/_\d+$/, "");

// A part's group: the assembly it was built in (glTF extras, from parts.assembly), else for
// untagged models its top-level node's name family.
export const tagged = (o: THREE.Object3D) => {
  for (let x: THREE.Object3D | null = o; x; x = x.parent) if (typeof x.userData.assembly === "string") return x;
  return null;
};
export function within(o: THREE.Object3D | null, scene: THREE.Object3D) {
  for (; o; o = o.parent) if (o === scene) return true;
  return false;
}

export function groupOf(o: THREE.Object3D, scene: THREE.Object3D) {
  const t = tagged(o);
  if (t) return t.userData.assembly as string;
  while (o.parent && o.parent !== scene) o = o.parent;
  return family(o.name);
}

// Blender's axes from the glTF's (exported y-up): x, -z, y; sizes just swap y and z.
export const blenderSize = (v: THREE.Vector3) => [v.x, v.z, v.y];
export const m2 = (v: number) => (v >= 1 ? `${v.toFixed(2)} m` : v >= 0.01 ? `${Math.round(v * 100)} cm`
  : v >= 0.001 ? `${(v * 1000).toFixed(1)} mm` : v >= 0.0001 ? `${(v * 1000).toFixed(2)} mm` : `${Math.round(v * 1e6)} µm`);
