import { Canvas, useFrame } from "@react-three/fiber"
import { useRef, useMemo } from "react"
import * as THREE from "three"
import { EffectComposer, Bloom } from "@react-three/postprocessing"

function MeshNet() {
  const groupRef = useRef<THREE.Group>(null)
  const count = 150

  // Generate initial static positions
  const positions = useMemo(() => {
    const arr = []
    for (let i = 0; i < count; i++) {
      arr.push(
        (Math.random() - 0.5) * 10, // x
        (Math.random() - 0.5) * 6,  // y
        (Math.random() - 0.5) * 4   // z
      )
    }
    return new Float32Array(arr)
  }, [count])

  // Buffer for animated points
  const pointsGeometry = useMemo(() => {
    const geo = new THREE.BufferGeometry()
    geo.setAttribute("position", new THREE.BufferAttribute(positions.slice(), 3))
    return geo
  }, [positions])

  // Refs for animation
  const posAttr = pointsGeometry.getAttribute("position") as THREE.BufferAttribute
  const basePositions = positions.slice() // keep originals for wave baseline

  // Animate each frame with wave deformation
  useFrame(({ clock }) => {
    const time = clock.elapsedTime
    for (let i = 0; i < count; i++) {
      const ix = i * 3
      const x = basePositions[ix]
      const y = basePositions[ix + 1]
      const z = basePositions[ix + 2]

      // Apply sine-based wave offset for flowing motion
      posAttr.array[ix] = x + Math.sin(time + y) * 0.2
      posAttr.array[ix + 1] = y + Math.sin(time * 0.5 + x) * 0.2
      posAttr.array[ix + 2] = z + Math.cos(time * 0.3 + y) * 0.2
    }
    posAttr.needsUpdate = true
  })

  // Create line segments each frame (dynamic connections)
  const lineGeometry = useMemo(() => new THREE.BufferGeometry(), [])
  useFrame(() => {
    const verts: number[] = []
    const colors: number[] = []
    const colorA = new THREE.Color("#fb923c") // Fikiri orange
    const colorB = new THREE.Color("#ef4444") // Fikiri red

    for (let i = 0; i < count; i++) {
      for (let j = i + 1; j < count; j++) {
        const dx = posAttr.array[i * 3] - posAttr.array[j * 3]
        const dy = posAttr.array[i * 3 + 1] - posAttr.array[j * 3 + 1]
        const dz = posAttr.array[i * 3 + 2] - posAttr.array[j * 3 + 2]
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz)
        if (dist < 2.5) { // threshold for connection
          // push positions
          verts.push(
            posAttr.array[i * 3], posAttr.array[i * 3 + 1], posAttr.array[i * 3 + 2],
            posAttr.array[j * 3], posAttr.array[j * 3 + 1], posAttr.array[j * 3 + 2]
          )
          // push gradient colors (orange to red)
          const c1 = colorA.clone().lerp(colorB, Math.random())
          const c2 = colorB.clone().lerp(colorA, Math.random())
          colors.push(c1.r, c1.g, c1.b, c2.r, c2.g, c2.b)
        }
      }
    }

    lineGeometry.setAttribute("position", new THREE.Float32BufferAttribute(verts, 3))
    lineGeometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3))
  })

  return (
    <group ref={groupRef}>
      {/* Glowing particles */}
      <points geometry={pointsGeometry}>
        <pointsMaterial size={0.06} color="#fb923c" />
      </points>

      {/* Connecting lines with gradient colors */}
      <lineSegments geometry={lineGeometry}>
        <lineBasicMaterial vertexColors opacity={0.5} transparent />
      </lineSegments>
    </group>
  )
}

export default function MeshBackground() {
  return (
    <Canvas
      camera={{ position: [0, 0, 8], fov: 60 }}
      style={{ position: "absolute", top: 0, left: 0, zIndex: -1 }}
    >
      <ambientLight intensity={0.4} />
      <MeshNet />

      {/* Glow / Bloom effect for that LangChain feel */}
      <EffectComposer>
        <Bloom
          intensity={1.5}
          luminanceThreshold={0.1}
          luminanceSmoothing={0.9}
          height={300}
        />
      </EffectComposer>
    </Canvas>
  )
}
