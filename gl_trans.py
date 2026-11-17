"""CapCut-style quick transitions using the open-source gl-transitions shaders (assets/gl/*.glsl), rendered with moderngl.
apply(src, dst, [(t0, "CrossZoom", 0.2), ...]): at t0 the new shot transitions in from a still of the last frame of the old shot."""
import re, subprocess, pathlib, numpy as np, moderngl
ROOT = pathlib.Path(__file__).parent; GLD = ROOT / "assets" / "gl"
VS = "#version 330\nin vec2 p; out vec2 uv_; void main(){ uv_ = p*0.5+0.5; gl_Position = vec4(p,0,1); }"
def _fs(name):
    src = (GLD / f"{name}.glsl").read_text(encoding="utf-8")
    src = re.sub(r"uniform\s+(\w+)\s+(\w+)\s*;\s*//\s*=\s*([^\n]+)", lambda m: f"uniform {m.group(1)} {m.group(2)} = {m.group(3).strip()};", src)
    return ("#version 330\nuniform sampler2D _from; uniform sampler2D _to; uniform float progress; uniform float ratio; in vec2 uv_; out vec4 fragColor;\n"
            "vec4 getFromColor(vec2 uv){ return texture(_from, uv); }\nvec4 getToColor(vec2 uv){ return texture(_to, uv); }\n" + src + "\nvoid main(){ fragColor = transition(uv_); }")
class GL:
    def __init__(self, w, h):
        self.w, self.h = w, h; self.ctx = moderngl.create_standalone_context(); c = self.ctx
        self.vbo = c.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], "f4").tobytes())
        self.tf = c.texture((w, h), 3); self.tt = c.texture((w, h), 3)
        for t in (self.tf, self.tt): t.filter = (moderngl.LINEAR, moderngl.LINEAR); t.repeat_x = t.repeat_y = False
        self.fbo = c.framebuffer(c.texture((w, h), 3)); self.progs = {}
    def prog(self, name):
        if name not in self.progs:
            p = self.ctx.program(vertex_shader=VS, fragment_shader=_fs(name)); self.progs[name] = (p, self.ctx.simple_vertex_array(p, self.vbo, "p"))
        return self.progs[name]
    def render(self, name, a, b, prog):
        p, vao = self.prog(name); self.tf.write(np.flipud(a).tobytes()); self.tt.write(np.flipud(b).tobytes())
        self.tf.use(0); self.tt.use(1)
        for k_, v_ in (("_from", 0), ("_to", 1), ("progress", float(prog)), ("ratio", self.w / self.h)):
            if k_ in p: p[k_].value = v_
        self.fbo.use(); self.ctx.clear(0, 0, 0); vao.render(moderngl.TRIANGLE_STRIP)
        return np.flipud(np.frombuffer(self.fbo.read(components=3), np.uint8).reshape(self.h, self.w, 3))
def apply(src, dst, trs, fps=30):
    pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(src)], capture_output=True, text=True).stdout.strip().split(",")
    w, h = int(pr[0]), int(pr[1]); fs = w * h * 3; gl = GL(w, h)
    rd = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(src), "-f", "rawvideo", "-pix_fmt", "rgb24", "-vf", f"fps={fps}", "-"], stdout=subprocess.PIPE)
    wr = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p", str(dst)], stdin=subprocess.PIPE)
    trs = sorted(trs); prev = None; i = 0; still = {}
    while True:
        buf = rd.stdout.read(fs)
        if len(buf) < fs: break
        fr = np.frombuffer(buf, np.uint8).reshape(h, w, 3); t = i / fps; out = fr
        for (t0, nm, d) in trs:
            if t0 <= t < t0 + d - 1e-6:
                if nm not in still or still[nm][0] != t0: still[nm] = (t0, prev if prev is not None else fr)
                out = gl.render(nm, still[nm][1], fr, (t - t0 + 1 / fps) / d); break
        wr.stdin.write(np.ascontiguousarray(out).tobytes()); prev = fr; i += 1
    wr.stdin.close(); wr.wait(); rd.wait()
