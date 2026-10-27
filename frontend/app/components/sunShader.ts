import * as THREE from 'three';

// The Sun in white light, as a telescope with a solar filter sees it: a
// near-white disc that darkens and warms toward the limb, with a fine
// granulation. All procedural, so it stays sharp at any zoom.

// Limb darkening: I(mu)/I(1) = 1 - u - v + u*mu + v*mu^2 (Allen, Astrophysical
// Quantities). u, v from SolarSoft darklimb_u/darklimb_v at 6500/5500/4500 A,
// standing in for the R/G/B channels. Blue darkens most, so the limb reddens.
const LIMB_U = new THREE.Vector3(0.802, 0.9139, 0.9782);
const LIMB_V = new THREE.Vector3(-0.1982, -0.2145, -0.164);

const vertexShader = /* glsl */ `
#include <common>
#include <logdepthbuf_pars_vertex>
varying vec3 vObj;
varying vec3 vNormalV;
varying vec3 vViewPos;
void main() {
  vObj = normalize(position);
  vNormalV = normalize(normalMatrix * normal);
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  vViewPos = mv.xyz;
  gl_Position = projectionMatrix * mv;
  #include <logdepthbuf_vertex>
}
`;

const fragmentShader = /* glsl */ `
#include <common>
#include <logdepthbuf_pars_fragment>
uniform vec3 uColor;
uniform vec3 uLimbU;
uniform vec3 uLimbV;
uniform float uTime;
varying vec3 vObj;
varying vec3 vNormalV;
varying vec3 vViewPos;

// 3D simplex noise (Ashima Arts / Stefan Gustavson, MIT).
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 permute(vec4 x) { return mod289(((x * 34.0) + 10.0) * x); }
vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }
float snoise(vec3 v) {
  const vec2 C = vec2(1.0 / 6.0, 1.0 / 3.0);
  const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
  vec3 i = floor(v + dot(v, C.yyy));
  vec3 x0 = v - i + dot(i, C.xxx);
  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min(g.xyz, l.zxy);
  vec3 i2 = max(g.xyz, l.zxy);
  vec3 x1 = x0 - i1 + C.xxx;
  vec3 x2 = x0 - i2 + C.yyy;
  vec3 x3 = x0 - D.yyy;
  i = mod289(i);
  vec4 p = permute(permute(permute(
    i.z + vec4(0.0, i1.z, i2.z, 1.0))
    + i.y + vec4(0.0, i1.y, i2.y, 1.0))
    + i.x + vec4(0.0, i1.x, i2.x, 1.0));
  float n_ = 0.142857142857;
  vec3 ns = n_ * D.wyz - D.xzx;
  vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
  vec4 x_ = floor(j * ns.z);
  vec4 y_ = floor(j - 7.0 * x_);
  vec4 x = x_ * ns.x + ns.yyyy;
  vec4 y = y_ * ns.x + ns.yyyy;
  vec4 h = 1.0 - abs(x) - abs(y);
  vec4 b0 = vec4(x.xy, y.xy);
  vec4 b1 = vec4(x.zw, y.zw);
  vec4 s0 = floor(b0) * 2.0 + 1.0;
  vec4 s1 = floor(b1) * 2.0 + 1.0;
  vec4 sh = -step(h, vec4(0.0));
  vec4 a0 = b0.xzyw + s0.xzyw * sh.xxyy;
  vec4 a1 = b1.xzyw + s1.xzyw * sh.zzww;
  vec3 p0 = vec3(a0.xy, h.x);
  vec3 p1 = vec3(a0.zw, h.y);
  vec3 p2 = vec3(a1.xy, h.z);
  vec3 p3 = vec3(a1.zw, h.w);
  vec4 norm = taylorInvSqrt(vec4(dot(p0, p0), dot(p1, p1), dot(p2, p2), dot(p3, p3)));
  p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
  vec4 m = max(0.5 - vec4(dot(x0, x0), dot(x1, x1), dot(x2, x2), dot(x3, x3)), 0.0);
  m = m * m;
  return 105.0 * dot(m * m, vec4(dot(p0, x0), dot(p1, x1), dot(p2, x2), dot(p3, x3)));
}

vec3 hash3(vec3 p) {
  p = vec3(dot(p, vec3(127.1, 311.7, 74.7)), dot(p, vec3(269.5, 183.3, 246.1)), dot(p, vec3(113.5, 271.9, 124.6)));
  return fract(sin(p) * 43758.5453123);
}

// Cellular noise: distance to the nearest and second-nearest feature point.
vec2 worley(vec3 p) {
  vec3 cell = floor(p);
  vec3 f = fract(p);
  float d1 = 8.0, d2 = 8.0;
  for (int z = -1; z <= 1; z++)
  for (int y = -1; y <= 1; y++)
  for (int x = -1; x <= 1; x++) {
    vec3 o = vec3(float(x), float(y), float(z));
    vec3 r = o + hash3(cell + o) - f;
    float d = dot(r, r);
    if (d < d1) { d2 = d1; d1 = d; } else if (d < d2) { d2 = d; }
  }
  return sqrt(vec2(d1, d2));
}

// 1 while a pattern of the given frequency spans several pixels, 0 once its
// cells shrink below one: far away the disc goes smooth instead of shimmering.
float detail(float freq) {
  float cellsPerPixel = length(fwidth(vObj)) * freq;
  return 1.0 - smoothstep(0.25, 0.8, cellsPerPixel);
}

// Granulation: bright cells parted by dark lanes, slowly reshaping.
float granulation(vec3 n, float freq) {
  float t = uTime;
  vec3 p = n * freq;
  p += 0.35 * vec3(snoise(p * 0.25 + t), snoise(p * 0.25 + t + 17.0), snoise(p * 0.25 + t + 41.0));
  vec2 w = worley(p);
  float lanes = smoothstep(0.0, 0.32, w.y - w.x);
  return lanes - 0.6;
}

void main() {
  #include <logdepthbuf_fragment>
  vec3 n = normalize(vObj);
  float mu = clamp(dot(normalize(vNormalV), normalize(-vViewPos)), 0.0, 1.0);

  // Surface pattern, centred on 0 so the disc's mean brightness stays put.
  float foreshorten = smoothstep(0.0, 0.25, mu);
  float g = 0.0;
  g += 0.13 * detail(380.0) * granulation(n, 380.0);
  g += 0.045 * detail(60.0) * snoise(n * 60.0 + uTime * 0.2);   // mesogranular mottling
  g += 0.025 * detail(14.0) * snoise(n * 14.0 - uTime * 0.05);  // large-scale unevenness
  float intensity = 1.0 + g * foreshorten;


  vec3 limb = 1.0 - uLimbU - uLimbV + uLimbU * mu + uLimbV * mu * mu;
  gl_FragColor = vec4(uColor * limb * intensity, 1.0);
  #include <colorspace_fragment>
}
`;

export function createSunMaterial(color: THREE.ColorRepresentation): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    vertexShader,
    fragmentShader,
    uniforms: {
      uColor: { value: new THREE.Color(color) },
      uLimbU: { value: LIMB_U },
      uLimbV: { value: LIMB_V },
      uTime: { value: 0 },
    },
  });
}

// Glow around the disc: a bright aureole hugging the limb that fades into a
// faint wide halo. discFraction is the disc's radius as a share of the sprite's
// half-width, so the falloff starts exactly at the limb.
export function createSunGlowTexture(discFraction: number): THREE.CanvasTexture {
  const size = 512;
  const half = size / 2;
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext('2d')!;
  const img = ctx.createImageData(size, size);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const r = Math.hypot(x + 0.5 - half, y + 0.5 - half) / half; // 0 centre, 1 sprite edge
      const s = Math.max(r - discFraction, 0) / (1 - discFraction); // 0 at limb, 1 at edge
      const aureole = 0.3 * Math.exp(-s * 10); // close to the limb's own brightness, so the edge reads as glowing
      const halo = 0.14 * Math.pow(discFraction / Math.max(r, discFraction), 2);
      const fade = 1 - Math.min(1, Math.max(0, (r - 0.7) / 0.3));
      const a = Math.min(1, (aureole + halo) * fade * fade);
      const i = (y * size + x) * 4;
      img.data[i] = 255;
      img.data[i + 1] = 246;
      img.data[i + 2] = 236;
      img.data[i + 3] = Math.round(a * 255);
    }
  }
  ctx.putImageData(img, 0, 0);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}
