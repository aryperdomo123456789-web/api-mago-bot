(() => {
  "use strict";
  const canvas = document.getElementById("mago-spatial-canvas");
  if (!canvas || !window.THREE) return;

  const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.7));
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(48, 1, 0.1, 1000);
  const core = new THREE.Group();
  const isOps = document.body.classList.contains("ops-surface");
  scene.add(core);

  const outerMaterial = new THREE.MeshBasicMaterial({ color: 0x00f0ff, wireframe: true, transparent: true, opacity: isOps ? 0.2 : 0.16 });
  const innerMaterial = new THREE.MeshBasicMaterial({ color: 0x8a2be2, wireframe: true, transparent: true, opacity: isOps ? 0.28 : 0.23 });
  const outer = new THREE.Mesh(new THREE.IcosahedronGeometry(2.25, 2), outerMaterial);
  const inner = new THREE.Mesh(new THREE.IcosahedronGeometry(1.42, 1), innerMaterial);
  core.add(outer, inner);

  const positions = new Float32Array(150 * 3);
  for (let index = 0; index < positions.length; index += 3) {
    positions[index] = (Math.random() - 0.5) * 15;
    positions[index + 1] = (Math.random() - 0.5) * 13;
    positions[index + 2] = (Math.random() - 0.5) * 8;
  }
  const particleGeometry = new THREE.BufferGeometry();
  particleGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const particles = new THREE.Points(particleGeometry, new THREE.PointsMaterial({ color: 0x00f0ff, size: 0.032, transparent: true, opacity: 0.38 }));
  scene.add(particles);

  let mouseX = 0;
  let mouseY = 0;
  let targetX = 0;
  let targetY = 0;
  const resize = () => {
    const width = window.innerWidth;
    const height = window.innerHeight;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height, false);
    camera.position.z = width < 760 ? 8.8 : 7.2;
    core.position.set(width < 760 ? 1.7 : (isOps ? 3.0 : 2.7), width < 760 ? 0.7 : 0.15, -0.5);
    outerMaterial.opacity = width < 760 ? 0.1 : (isOps ? 0.2 : 0.16);
    innerMaterial.opacity = width < 760 ? 0.15 : (isOps ? 0.28 : 0.23);
  };
  const pointer = (event) => {
    const point = event.touches?.[0] || event;
    mouseX = (point.clientX / window.innerWidth) * 2 - 1;
    mouseY = -(point.clientY / window.innerHeight) * 2 + 1;
  };
  window.addEventListener("resize", resize, { passive: true });
  window.addEventListener("mousemove", pointer, { passive: true });
  window.addEventListener("touchmove", pointer, { passive: true });
  resize();

  const animate = () => {
    if (!reduceMotion) requestAnimationFrame(animate);
    targetX += (mouseX * 0.16 - targetX) * 0.025;
    targetY += (mouseY * 0.12 - targetY) * 0.025;
    core.rotation.y += reduceMotion ? 0 : 0.0018;
    core.rotation.x += reduceMotion ? 0 : 0.0007;
    core.rotation.y += (targetX - core.rotation.y) * 0.002;
    core.rotation.x += (targetY - core.rotation.x) * 0.002;
    particles.rotation.y += reduceMotion ? 0 : 0.00025;
    renderer.render(scene, camera);
  };
  animate();
})();
