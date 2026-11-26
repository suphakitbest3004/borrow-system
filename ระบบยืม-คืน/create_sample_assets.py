import os

svg_icons = {
    "multimeter.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f8fafc"/>
      <stop offset="100%" stop-color="#e2e8f0"/>
    </linearGradient>
    <linearGradient id="bodyGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#f59e0b"/>
      <stop offset="100%" stop-color="#d97706"/>
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#bgGrad1)"/>
  <!-- Multimeter Body -->
  <rect x="130" y="40" width="140" height="220" rx="24" fill="url(#bodyGrad)" stroke="#b45309" stroke-width="4"/>
  <rect x="145" y="60" width="110" height="190" rx="16" fill="#1e293b"/>
  <!-- LCD Screen -->
  <rect x="155" y="75" width="90" height="45" rx="6" fill="#ecfccb" stroke="#84cc16" stroke-width="2"/>
  <text x="200" y="105" font-family="monospace" font-size="22" font-weight="bold" fill="#1e293b" text-anchor="middle">220.4 V</text>
  <!-- Knob -->
  <circle cx="200" cy="165" r="28" fill="#334155" stroke="#64748b" stroke-width="3"/>
  <circle cx="200" cy="165" r="16" fill="#0f172a"/>
  <line x1="200" y1="140" x2="200" y2="152" stroke="#f59e0b" stroke-width="4" stroke-linecap="round"/>
  <!-- Ports -->
  <circle cx="170" cy="225" r="8" fill="#ef4444"/>
  <circle cx="200" cy="225" r="8" fill="#0f172a"/>
  <circle cx="230" cy="225" r="8" fill="#10b981"/>
  <!-- Badge -->
  <rect x="20" y="20" width="100" height="26" rx="13" fill="#ffffff" stroke="#cbd5e1" stroke-width="1"/>
  <text x="70" y="37" font-family="sans-serif" font-size="11" font-weight="600" fill="#475569" text-anchor="middle">ครุภัณฑ์ไฟฟ้า</text>
</svg>""",

    "projector.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad2" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f8fafc"/>
      <stop offset="100%" stop-color="#e2e8f0"/>
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#bgGrad2)"/>
  <!-- Projector Body -->
  <rect x="80" y="110" width="240" height="90" rx="16" fill="#ffffff" stroke="#cbd5e1" stroke-width="3"/>
  <rect x="80" y="185" width="240" height="15" fill="#f1f5f9"/>
  <!-- Feet -->
  <rect x="110" y="200" width="24" height="10" rx="3" fill="#64748b"/>
  <rect x="266" y="200" width="24" height="10" rx="3" fill="#64748b"/>
  <!-- Lens -->
  <circle cx="140" cy="155" r="32" fill="#0284c7" stroke="#38bdf8" stroke-width="5"/>
  <circle cx="140" cy="155" r="20" fill="#0f172a"/>
  <circle cx="132" cy="147" r="6" fill="#bae6fd" opacity="0.8"/>
  <!-- Buttons / Vents -->
  <rect x="220" y="130" width="60" height="6" rx="3" fill="#cbd5e1"/>
  <rect x="220" y="142" width="60" height="6" rx="3" fill="#cbd5e1"/>
  <rect x="220" y="154" width="60" height="6" rx="3" fill="#cbd5e1"/>
  <circle cx="295" cy="135" r="5" fill="#22c55e"/>
  <!-- Badge -->
  <rect x="20" y="20" width="120" height="26" rx="13" fill="#ffffff" stroke="#cbd5e1" stroke-width="1"/>
  <text x="80" y="37" font-family="sans-serif" font-size="11" font-weight="600" fill="#475569" text-anchor="middle">ครุภัณฑ์โสตทัศน์</text>
</svg>""",

    "oscilloscope.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad3" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f8fafc"/>
      <stop offset="100%" stop-color="#e2e8f0"/>
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#bgGrad3)"/>
  <!-- Oscilloscope Body -->
  <rect x="60" y="60" width="280" height="180" rx="14" fill="#334155" stroke="#1e293b" stroke-width="4"/>
  <!-- Screen -->
  <rect x="80" y="80" width="150" height="140" rx="8" fill="#090d16" stroke="#475569" stroke-width="2"/>
  <!-- Sine wave on grid -->
  <path d="M 85 150 Q 115 100, 140 150 T 195 150 T 225 150" fill="none" stroke="#22c55e" stroke-width="3"/>
  <!-- Knobs Panel -->
  <circle cx="265" cy="100" r="14" fill="#64748b" stroke="#cbd5e1" stroke-width="2"/>
  <circle cx="305" cy="100" r="14" fill="#64748b" stroke="#cbd5e1" stroke-width="2"/>
  <circle cx="265" cy="140" r="14" fill="#64748b" stroke="#cbd5e1" stroke-width="2"/>
  <circle cx="305" cy="140" r="14" fill="#64748b" stroke="#cbd5e1" stroke-width="2"/>
  <circle cx="260" cy="195" r="9" fill="#e2e8f0" stroke="#94a3b8" stroke-width="2"/>
  <circle cx="285" cy="195" r="9" fill="#e2e8f0" stroke="#94a3b8" stroke-width="2"/>
  <circle cx="310" cy="195" r="9" fill="#e2e8f0" stroke="#94a3b8" stroke-width="2"/>
  <!-- Badge -->
  <rect x="20" y="20" width="130" height="26" rx="13" fill="#ffffff" stroke="#cbd5e1" stroke-width="1"/>
  <text x="85" y="37" font-family="sans-serif" font-size="11" font-weight="600" fill="#475569" text-anchor="middle">ครุภัณฑ์วิทยาศาสตร์</text>
</svg>""",

    "soldering.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad4" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f8fafc"/>
      <stop offset="100%" stop-color="#e2e8f0"/>
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#bgGrad4)"/>
  <!-- Station Base -->
  <rect x="100" y="90" width="140" height="130" rx="16" fill="#1e3a8a" stroke="#172554" stroke-width="3"/>
  <!-- LED Screen -->
  <rect x="125" y="115" width="90" height="36" rx="6" fill="#0f172a"/>
  <text x="170" y="140" font-family="monospace" font-size="20" font-weight="bold" fill="#ef4444" text-anchor="middle">350 °C</text>
  <!-- Buttons -->
  <circle cx="145" cy="180" r="12" fill="#3b82f6"/>
  <circle cx="195" cy="180" r="12" fill="#3b82f6"/>
  <!-- Iron holder -->
  <rect x="260" y="130" width="50" height="90" rx="8" fill="#64748b"/>
  <line x1="285" y1="90" x2="285" y2="150" stroke="#cbd5e1" stroke-width="8" stroke-linecap="round"/>
  <!-- Badge -->
  <rect x="20" y="20" width="130" height="26" rx="13" fill="#ffffff" stroke="#cbd5e1" stroke-width="1"/>
  <text x="85" y="37" font-family="sans-serif" font-size="11" font-weight="600" fill="#475569" text-anchor="middle">ครุภัณฑ์ช่างไฟฟ้า</text>
</svg>""",

    "drill.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad5" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f8fafc"/>
      <stop offset="100%" stop-color="#e2e8f0"/>
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#bgGrad5)"/>
  <!-- Drill Chuck -->
  <rect x="70" y="105" width="40" height="30" rx="4" fill="#334155"/>
  <polygon points="70,120 40,117 40,123" fill="#94a3b8"/>
  <!-- Drill Body -->
  <path d="M 110 95 L 240 95 Q 260 95, 260 115 L 260 145 Q 250 160, 220 165 L 220 220 Q 220 235, 205 235 L 180 235 Q 165 235, 165 220 L 165 170 L 110 145 Z" fill="#0284c7" stroke="#0369a1" stroke-width="3"/>
  <rect x="160" y="235" width="55" height="25" rx="4" fill="#0f172a"/>
  <!-- Trigger -->
  <path d="M 165 155 Q 150 155, 150 168 Q 150 180, 165 180 Z" fill="#ef4444"/>
  <!-- Badge -->
  <rect x="20" y="20" width="130" height="26" rx="13" fill="#ffffff" stroke="#cbd5e1" stroke-width="1"/>
  <text x="85" y="37" font-family="sans-serif" font-size="11" font-weight="600" fill="#475569" text-anchor="middle">ครุภัณฑ์โรงงาน</text>
</svg>""",

    "camera.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad6" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f8fafc"/>
      <stop offset="100%" stop-color="#e2e8f0"/>
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#bgGrad6)"/>
  <!-- Camera Body -->
  <rect x="80" y="90" width="240" height="140" rx="20" fill="#1e293b" stroke="#0f172a" stroke-width="3"/>
  <!-- Pentaprism bump -->
  <polygon points="150,90 250,90 230,65 170,65" fill="#1e293b" stroke="#0f172a" stroke-width="3"/>
  <!-- Lens -->
  <circle cx="200" cy="160" r="50" fill="#334155" stroke="#64748b" stroke-width="6"/>
  <circle cx="200" cy="160" r="34" fill="#0f172a"/>
  <circle cx="190" cy="150" r="10" fill="#38bdf8" opacity="0.6"/>
  <!-- Shutter button -->
  <rect x="100" y="80" width="24" height="10" rx="3" fill="#94a3b8"/>
  <!-- Badge -->
  <rect x="20" y="20" width="130" height="26" rx="13" fill="#ffffff" stroke="#cbd5e1" stroke-width="1"/>
  <text x="85" y="37" font-family="sans-serif" font-size="11" font-weight="600" fill="#475569" text-anchor="middle">ครุภัณฑ์คอมพิวเตอร์</text>
</svg>""",

    "solder_wire.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad7" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f8fafc"/>
      <stop offset="100%" stop-color="#e2e8f0"/>
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#bgGrad7)"/>
  <!-- Spool -->
  <ellipse cx="200" cy="90" rx="70" ry="25" fill="#3b82f6" stroke="#1d4ed8" stroke-width="3"/>
  <rect x="130" y="90" width="140" height="90" fill="#94a3b8"/>
  <!-- Solder core -->
  <ellipse cx="200" cy="135" rx="60" ry="18" fill="#e2e8f0"/>
  <ellipse cx="200" cy="180" rx="70" ry="25" fill="#3b82f6" stroke="#1d4ed8" stroke-width="3"/>
  <!-- Label on roll -->
  <rect x="145" y="115" width="110" height="40" rx="4" fill="#ffffff"/>
  <text x="200" y="132" font-family="sans-serif" font-size="10" font-weight="bold" fill="#1e293b" text-anchor="middle">LEAD FREE 0.8mm</text>
  <text x="200" y="146" font-family="sans-serif" font-size="9" fill="#64748b" text-anchor="middle">FLUX CORE 500G</text>
  <!-- Wire sticking out -->
  <path d="M 270 140 Q 300 150, 310 190 T 325 230" fill="none" stroke="#cbd5e1" stroke-width="4"/>
  <!-- Badge -->
  <rect x="20" y="20" width="110" height="26" rx="13" fill="#ffffff" stroke="#cbd5e1" stroke-width="1"/>
  <text x="75" y="37" font-family="sans-serif" font-size="11" font-weight="600" fill="#475569" text-anchor="middle">วัสดุสิ้นเปลือง</text>
</svg>"""
}

target_dir = os.path.join(os.path.dirname(__file__), "static", "uploads")
os.makedirs(target_dir, exist_ok=True)

for fname, content in svg_icons.items():
    path = os.path.join(target_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

print(f"Created {len(svg_icons)} sample equipment SVG images in {target_dir}")
