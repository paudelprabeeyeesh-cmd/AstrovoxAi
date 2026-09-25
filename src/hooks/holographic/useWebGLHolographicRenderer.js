import { useRef, useEffect, useCallback } from 'react'
import { HOLOGRAPHIC_CONFIG, HOLOGRAPHIC_COLORS } from '../utils/holographic/HolographicConfig'

export function useWebGLHolographicRenderer() {
  const canvasRef = useRef(null)
  const glRef = useRef(null)
  const programRef = useRef(null)
  const animationFrameRef = useRef(null)
  const startTimeRef = useRef(Date.now())

  const initWebGL = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return false

    const gl = canvas.getContext('webgl2', {
      alpha: true,
      antialias: true,
      depth: false,
      stencil: false,
      premultipliedAlpha: true
    })

    if (!gl) {
      console.warn('WebGL2 not supported, falling back to WebGL1')
      const gl1 = canvas.getContext('webgl', {
        alpha: true,
        antialias: true,
        depth: false
      })
      if (!gl1) return false
      glRef.current = gl1
      return true
    }

    glRef.current = gl
    return true
  }, [])

  const createShader = useCallback((gl, type, source) => {
    const shader = gl.createShader(type)
    gl.shaderSource(shader, source)
    gl.compileShader(shader)

    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      console.error('Shader compile error:', gl.getShaderInfoLog(shader))
      gl.deleteShader(shader)
      return null
    }

    return shader
  }, [])

  const createProgram = useCallback((gl, vertexShader, fragmentShader) => {
    const program = gl.createProgram()
    gl.attachShader(program, vertexShader)
    gl.attachShader(program, fragmentShader)
    gl.linkProgram(program)

    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.error('Program link error:', gl.getProgramInfoLog(program))
      gl.deleteProgram(program)
      return null
    }

    return program
  }, [])

  const initShaders = useCallback(() => {
    const gl = glRef.current
    if (!gl) return false

    const vertexShaderSource = `
      attribute vec2 a_position;
      attribute vec2 a_texCoord;
      varying vec2 v_texCoord;
      void main() {
        gl_Position = vec4(a_position, 0.0, 1.0);
        v_texCoord = a_texCoord;
      }
    `

    const fragmentShaderSource = `
      precision highp float;
      varying vec2 v_texCoord;
      uniform float u_time;
      uniform vec2 u_resolution;
      uniform vec2 u_mouse;
      uniform float u_hoverIntensity;
      uniform float u_gestureProgress;
      uniform int u_gestureType;
      uniform float u_depth;
      uniform float u_hologramPersistence;
      uniform float u_diffraction;
      uniform float u_interference;
      uniform float u_chromaticAberration;
      uniform float u_scanlineOpacity;
      uniform float u_noiseAmount;
      uniform float u_glitchIntensity;
      uniform float u_consciousness;
      uniform float u_quantum;
      uniform vec3 u_primaryColor;
      uniform vec3 u_secondaryColor;
      uniform vec3 u_accentColor;

      float random(vec2 st) {
        return fract(sin(dot(st.xy, vec2(12.9898, 78.233))) * 43758.5453123);
      }

      float noise(vec2 st) {
        vec2 i = floor(st);
        vec2 f = fract(st);
        float a = random(i);
        float b = random(i + vec2(1.0, 0.0));
        float c = random(i + vec2(0.0, 1.0));
        float d = random(i + vec2(1.0, 1.0));
        vec2 u = f * f * (3.0 - 2.0 * f);
        return mix(a, b, u.x) + (c - a) * u.y * (1.0 - u.x) + (d - b) * u.x * u.y;
      }

      float hologramPattern(vec2 uv, float time) {
        float wave = sin(uv.x * 20.0 + time * 2.0) * 0.5 + 0.5;
        wave *= sin(uv.y * 15.0 - time * 1.5) * 0.5 + 0.5;
        wave += sin(length(uv - 0.5) * 30.0 - time * 3.0) * 0.3;
        return wave * 0.5 + 0.5;
      }

      float lightField(vec2 uv, vec2 mouse, float depth) {
        float lens = 0.02 + depth * 0.01;
        vec2 offset = (uv - mouse) * lens;
        float field = 0.0;
        for (float i = -3.0; i <= 3.0; i += 1.0) {
          for (float j = -3.0; j <= 3.0; j += 1.0) {
            vec2 sampleUV = uv + vec2(i, j) * 0.0015;
            float ca = length(sampleUV - mouse) * 0.002;
            sampleUV += normalize(sampleUV - mouse + 0.001) * ca;
            field += hologramPattern(sampleUV, u_time + length(vec2(i, j)) * 0.08);
          }
        }
        return field / 49.0;
      }

      float volumetricFog(vec2 uv, float depth) {
        float fog = 0.0;
        for (float i = 0.0; i < 8.0; i += 1.0) {
          float z = i / 8.0;
          float layerScale = 1.0 + z * 0.6;
          vec2 layerUV = uv * layerScale + u_time * 0.08 * (1.0 - z);
          float layerDepth = depth * (1.0 - z * 0.5);
          fog += hologramPattern(layerUV, u_time + z) * layerDepth * 0.15;
        }
        return fog;
      }

      float diffractionGrating(vec2 uv, float angle) {
        float grating = sin((uv.x * cos(angle) + uv.y * sin(angle)) * 80.0 + u_time * 2.5);
        grating = grating * 0.5 + 0.5;
        return grating;
      }

      float depthOfField(vec2 uv, float focusDepth, float aperture) {
        float centerDist = length(uv - 0.5);
        float blur = abs(centerDist - focusDepth) * aperture;
        return smoothstep(0.0, 0.3, blur);
      }

      vec3 hologramColor(vec2 uv, float intensity, float depth) {
        float wave = hologramPattern(uv, u_time);
        float field = lightField(uv, u_mouse, depth);
        float fog = volumetricFog(uv, depth);
        float grating = diffractionGrating(uv, u_time * 0.5);

        vec3 color = vec3(0.0);
        color += u_primaryColor * wave * intensity * 0.5;
        color += u_secondaryColor * field * intensity * 0.3;
        color += u_accentColor * fog * intensity * 0.2;
        color += vec3(1.0) * grating * intensity * 0.05;

        float alpha = intensity * (wave * 0.5 + field * 0.3 + fog * 0.2);
        alpha *= smoothstep(0.0, 0.2, intensity);
        alpha *= smoothstep(1.0, 0.8, intensity);

        return vec3(color, alpha);
      }

      void main() {
        vec2 uv = v_texCoord;
        vec2 aspect = vec2(u_resolution.x / u_resolution.y, 1.0);
        vec2 centeredUV = (uv - 0.5) * aspect + 0.5;

        float mouseDistance = length(centeredUV - u_mouse);
        float hoverEffect = smoothstep(0.5, 0.0, mouseDistance) * u_hoverIntensity;

        float time = u_time;
        float glitchOffset = 0.0;
        if (u_glitchIntensity > 0.0) {
          float glitchLine = step(0.98, random(vec2(floor(uv.y * 80.0), floor(time * 12.0))));
          glitchOffset = glitchLine * u_glitchIntensity * (random(vec2(time, uv.y)) - 0.5) * 0.12;
        }

        vec2 distortedUV = centeredUV;
        distortedUV.x += glitchOffset;
        distortedUV += (noise(uv * 12.0 + time) - 0.5) * u_noiseAmount;

        float ca = u_chromaticAberration * hoverEffect;
        float r = hologramPattern(distortedUV + vec2(ca * 0.012, 0.0), time).r;
        float g = hologramPattern(distortedUV, time).g;
        float b = hologramPattern(distortedUV - vec2(ca * 0.012, 0.0), time).b;
        float wave = (r + g + b) / 3.0;

        float depth = u_depth + hoverEffect * 0.2;
        float focusDepth = 0.5;
        float aperture = 0.03 + u_chromaticAberration * 0.01;
        float dof = depthOfField(distortedUV, focusDepth, aperture);

        float intensity = smoothstep(0.0, 0.5, wave) * (0.5 + hoverEffect);
        intensity *= 0.7 + sin(time * 2.2 + uv.x * 5.5) * 0.3;
        intensity = mix(intensity, intensity * u_hologramPersistence, 0.5);
        intensity *= (1.0 - dof * 0.3);

        float scanline = sin(uv.y * u_resolution.y * 3.0) * u_scanlineOpacity;
        float holographicNoise = noise(uv * 120.0 + time) * u_noiseAmount;

        float interference = 0.0;
        for (float i = 0.0; i < 4.0; i += 1.0) {
          interference += sin(length(centeredUV - 0.5) * 25.0 - time * 3.5 + i) * u_interference * 0.25;
        }
        interference = interference * 0.5 + 0.5;

        vec3 hColor = hologramColor(distortedUV, intensity, depth);

        vec3 color = hColor.rgb;
        color += scanline * 0.12;
        color += holographicNoise * 0.06;
        color += interference * u_primaryColor * 0.12;

        float diffraction = diffractionGrating(distortedUV, time * 0.35) * u_diffraction;
        color += u_accentColor * diffraction * 0.12;

        color += u_primaryColor * hoverEffect * 0.25;
        color += u_quantum * u_quantumColor * 0.18;

        color = pow(color, vec3(0.95));
        color = clamp(color, 0.0, 1.0);

        float alpha = hColor.a;
        alpha = clamp(alpha, 0.0, 1.0);
        alpha *= smoothstep(0.0, 0.15, intensity);
        alpha *= smoothstep(1.0, 0.85, intensity);

        gl_FragColor = vec4(color, alpha);
      }
    `

    const vertexShader = createShader(gl, gl.VERTEX_SHADER, vertexShaderSource)
    const fragmentShader = createShader(gl, gl.FRAGMENT_SHADER, fragmentShaderSource)

    if (!vertexShader || !fragmentShader) return false

    const program = createProgram(gl, vertexShader, fragmentShader)
    if (!program) return false

    programRef.current = program

    const positions = new Float32Array([
      -1, -1, 0, 0,
       1, -1, 1, 0,
      -1,  1, 0, 1,
       1,  1, 1, 1
    ])

    const buffer = gl.createBuffer()
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer)
    gl.bufferData(gl.ARRAY_BUFFER, positions, gl.STATIC_DRAW)

    const positionLoc = gl.getAttribLocation(program, 'a_position')
    const texCoordLoc = gl.getAttribLocation(program, 'a_texCoord')

    gl.enableVertexAttribArray(positionLoc)
    gl.vertexAttribPointer(positionLoc, 2, gl.FLOAT, false, 16, 0)

    gl.enableVertexAttribArray(texCoordLoc)
    gl.vertexAttribPointer(texCoordLoc, 2, gl.FLOAT, false, 16, 8)

    return true
  }, [createShader, createProgram])

  const resizeCanvas = useCallback(() => {
    const canvas = canvasRef.current
    const gl = glRef.current
    if (!canvas || !gl) return

    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()
    const width = rect.width * dpr
    const height = rect.height * dpr

    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width
      canvas.height = height
      gl.viewport(0, 0, width, height)
    }
  }, [])

  const render = useCallback((params = {}) => {
    const gl = glRef.current
    const program = programRef.current
    if (!gl || !program) return

    resizeCanvas()

    const time = (Date.now() - startTimeRef.current) / 1000

    gl.useProgram(program)

    const uniforms = {
      u_time: time,
      u_resolution: [canvasRef.current?.width || 1, canvasRef.current?.height || 1],
      u_mouse: params.mouse || [0.5, 0.5],
      u_hoverIntensity: params.hoverIntensity || 0,
      u_gestureProgress: params.gestureProgress || 0,
      u_gestureType: params.gestureType || 0,
      u_depth: params.depth || 0.5,
      u_hologramPersistence: params.persistence || HOLOGRAPHIC_CONFIG.hologram.persistence,
      u_diffraction: params.diffraction || HOLOGRAPHIC_CONFIG.hologram.diffraction,
      u_interference: params.interference || HOLOGRAPHIC_CONFIG.hologram.interference,
      u_chromaticAberration: params.chromaticAberration || HOLOGRAPHIC_CONFIG.glitch.chromaticAberration,
      u_scanlineOpacity: params.scanlineOpacity || HOLOGRAPHIC_CONFIG.glitch.scanlineOpacity,
      u_noiseAmount: params.noiseAmount || HOLOGRAPHIC_CONFIG.glitch.noiseAmount,
      u_glitchIntensity: params.glitchIntensity || 0,
      u_consciousness: params.consciousness || 0,
      u_quantum: params.quantum || 0,
      u_primaryColor: hexToRGB(HOLOGRAPHIC_COLORS.primary),
      u_secondaryColor: hexToRGB(HOLOGRAPHIC_COLORS.secondary),
      u_accentColor: hexToRGB(HOLOGRAPHIC_COLORS.accent),
      u_quantumColor: hexToRGB(HOLOGRAPHIC_COLORS.quantum)
    }

    Object.entries(uniforms).forEach(([name, value]) => {
      const loc = gl.getUniformLocation(program, name)
      if (loc === null) return

      if (Array.isArray(value)) {
        if (value.length === 2) gl.uniform2fv(loc, value)
        else if (value.length === 3) gl.uniform3fv(loc, value)
        else if (value.length === 4) gl.uniform4fv(loc, value)
      } else if (typeof value === 'number') {
        gl.uniform1f(loc, value)
      }
    })

    gl.clearColor(0, 0, 0, 0)
    gl.clear(gl.COLOR_BUFFER_BIT)
    gl.enable(gl.BLEND)
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA)
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4)
  }, [resizeCanvas])

  const startRenderLoop = useCallback((paramsCallback) => {
    const loop = () => {
      const params = typeof paramsCallback === 'function' ? paramsCallback() : paramsCallback
      render(params)
      animationFrameRef.current = requestAnimationFrame(loop)
    }
    loop()
  }, [render])

  const stopRenderLoop = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current)
      animationFrameRef.current = null
    }
  }, [])

  useEffect(() => {
    const initialized = initWebGL() && initShaders()
    if (initialized) {
      startRenderLoop()
    }

    return () => {
      stopRenderLoop()
    }
  }, [initWebGL, initShaders, startRenderLoop, stopRenderLoop])

  return {
    canvasRef,
    render,
    startRenderLoop,
    stopRenderLoop,
    initWebGL,
    initShaders
  }
}

function hexToRGB(hex) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
  return result ? [
    parseInt(result[1], 16) / 255,
    parseInt(result[2], 16) / 255,
    parseInt(result[3], 16) / 255
  ] : [0, 0, 0]
}
