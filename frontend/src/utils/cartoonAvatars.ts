/**
 * Cartoon Avatar Presets and Image Processing Utilities
 */

export interface CartoonAvatar {
  id: string;
  name: string;
  category: string;
  svgDataUrl: string;
}

const createSvgDataUrl = (svgContent: string): string => {
  return `data:image/svg+xml;utf8,${encodeURIComponent(svgContent.trim())}`;
};

export const CARTOON_AVATARS: CartoonAvatar[] = [
  {
    id: 'cyber-bot',
    name: 'Cyber Bot',
    category: 'Robots',
    svgDataUrl: createSvgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <defs>
          <linearGradient id="bg_bot" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#0284c7" />
            <stop offset="100%" stop-color="#38bdf8" />
          </linearGradient>
          <linearGradient id="metal_bot" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stop-color="#f1f5f9" />
            <stop offset="100%" stop-color="#cbd5e1" />
          </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="50" fill="url(#bg_bot)" />
        <!-- Antenna -->
        <line x1="50" y1="26" x2="50" y2="14" stroke="#e2e8f0" stroke-width="4" stroke-linecap="round" />
        <circle cx="50" cy="13" r="5" fill="#facc15" />
        <!-- Ears -->
        <rect x="20" y="42" width="6" height="16" rx="3" fill="#94a3b8" />
        <rect x="74" y="42" width="6" height="16" rx="3" fill="#94a3b8" />
        <!-- Head -->
        <rect x="24" y="26" width="52" height="46" rx="14" fill="url(#metal_bot)" stroke="#0f172a" stroke-width="2.5" />
        <!-- Screen / Visor -->
        <rect x="30" y="34" width="40" height="22" rx="8" fill="#0f172a" />
        <!-- Glowing Eyes -->
        <circle cx="41" cy="45" r="5" fill="#38bdf8" />
        <circle cx="42" cy="43.5" r="1.8" fill="#ffffff" />
        <circle cx="59" cy="45" r="5" fill="#38bdf8" />
        <circle cx="60" cy="43.5" r="1.8" fill="#ffffff" />
        <!-- Smile -->
        <path d="M42 62 Q50 67 58 62" stroke="#0f172a" stroke-width="2.5" stroke-linecap="round" fill="none" />
        <!-- Cheeks -->
        <circle cx="34" cy="58" r="3" fill="#f43f5e" opacity="0.4" />
        <circle cx="66" cy="58" r="3" fill="#f43f5e" opacity="0.4" />
      </svg>
    `),
  },
  {
    id: 'cosmo-cat',
    name: 'Cosmo Cat',
    category: 'Animals',
    svgDataUrl: createSvgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <defs>
          <linearGradient id="bg_cat" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#6366f1" />
            <stop offset="100%" stop-color="#a855f7" />
          </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="50" fill="url(#bg_cat)" />
        <!-- Sparkles -->
        <polygon points="20,20 22,25 27,27 22,29 20,34 18,29 13,27 18,25" fill="#fef08a" opacity="0.8" />
        <polygon points="80,24 81.5,27.5 85,29 81.5,30.5 80,34 78.5,30.5 75,29 78.5,27.5" fill="#fef08a" opacity="0.7" />
        <!-- Cat Ears -->
        <polygon points="28,42 22,18 42,30" fill="#f8fafc" stroke="#1e1b4b" stroke-width="2.5" stroke-linejoin="round" />
        <polygon points="30,38 26,24 38,32" fill="#f472b6" />
        <polygon points="72,42 78,18 58,30" fill="#f8fafc" stroke="#1e1b4b" stroke-width="2.5" stroke-linejoin="round" />
        <polygon points="70,38 74,24 62,32" fill="#f472b6" />
        <!-- Cat Head -->
        <ellipse cx="50" cy="55" rx="30" ry="26" fill="#f8fafc" stroke="#1e1b4b" stroke-width="2.5" />
        <!-- Eyes -->
        <ellipse cx="39" cy="52" rx="4.5" ry="6" fill="#1e1b4b" />
        <circle cx="40.5" cy="50" r="2" fill="#ffffff" />
        <ellipse cx="61" cy="52" rx="4.5" ry="6" fill="#1e1b4b" />
        <circle cx="62.5" cy="50" r="2" fill="#ffffff" />
        <!-- Nose -->
        <polygon points="50,60 47,57 53,57" fill="#f472b6" />
        <!-- Mouth -->
        <path d="M46 62 Q50 65 50 61 Q50 65 54 62" stroke="#1e1b4b" stroke-width="2" stroke-linecap="round" fill="none" />
        <!-- Whiskers -->
        <line x1="22" y1="53" x2="33" y2="55" stroke="#94a3b8" stroke-width="1.8" stroke-linecap="round" />
        <line x1="21" y1="59" x2="32" y2="59" stroke="#94a3b8" stroke-width="1.8" stroke-linecap="round" />
        <line x1="78" y1="53" x2="67" y2="55" stroke="#94a3b8" stroke-width="1.8" stroke-linecap="round" />
        <line x1="79" y1="59" x2="68" y2="59" stroke="#94a3b8" stroke-width="1.8" stroke-linecap="round" />
      </svg>
    `),
  },
  {
    id: 'speedy-fox',
    name: 'Sparky Fox',
    category: 'Animals',
    svgDataUrl: createSvgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <defs>
          <linearGradient id="bg_fox" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#ea580c" />
            <stop offset="100%" stop-color="#fb923c" />
          </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="50" fill="url(#bg_fox)" />
        <!-- Ears -->
        <polygon points="25,44 18,16 43,30" fill="#f97316" stroke="#431407" stroke-width="2.5" stroke-linejoin="round" />
        <polygon points="27,38 23,23 38,32" fill="#431407" />
        <polygon points="75,44 82,16 57,30" fill="#f97316" stroke="#431407" stroke-width="2.5" stroke-linejoin="round" />
        <polygon points="73,38 77,23 62,32" fill="#431407" />
        <!-- Head -->
        <path d="M22 48 C22 34 78 34 78 48 C78 68 50 78 50 78 C50 78 22 68 22 48 Z" fill="#f97316" stroke="#431407" stroke-width="2.5" />
        <!-- White Muzzle -->
        <path d="M24 49 C34 50 42 62 50 78 C58 62 66 50 76 49 C78 64 50 77 50 77 C50 77 22 64 24 49 Z" fill="#ffffff" />
        <!-- Eyes -->
        <ellipse cx="37" cy="46" rx="4" ry="5.5" fill="#431407" />
        <circle cx="38.5" cy="44.5" r="1.8" fill="#ffffff" />
        <ellipse cx="63" cy="46" rx="4" ry="5.5" fill="#431407" />
        <circle cx="64.5" cy="44.5" r="1.8" fill="#ffffff" />
        <!-- Nose -->
        <ellipse cx="50" cy="74" rx="4" ry="3" fill="#431407" />
      </svg>
    `),
  },
  {
    id: 'boba-panda',
    name: 'Boba Panda',
    category: 'Animals',
    svgDataUrl: createSvgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <defs>
          <linearGradient id="bg_panda" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#059669" />
            <stop offset="100%" stop-color="#34d399" />
          </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="50" fill="url(#bg_panda)" />
        <!-- Ears -->
        <circle cx="28" cy="30" r="13" fill="#1e293b" />
        <circle cx="28" cy="30" r="7" fill="#475569" />
        <circle cx="72" cy="30" r="13" fill="#1e293b" />
        <circle cx="72" cy="30" r="7" fill="#475569" />
        <!-- Head -->
        <circle cx="50" cy="54" r="30" fill="#f8fafc" stroke="#0f172a" stroke-width="2.5" />
        <!-- Eye Patches -->
        <ellipse cx="38" cy="51" rx="8" ry="10" transform="rotate(-15 38 51)" fill="#1e293b" />
        <circle cx="38" cy="50" r="3" fill="#ffffff" />
        <circle cx="39" cy="49" r="1" fill="#0f172a" />
        <ellipse cx="62" cy="51" rx="8" ry="10" transform="rotate(15 62 51)" fill="#1e293b" />
        <circle cx="62" cy="50" r="3" fill="#ffffff" />
        <circle cx="63" cy="49" r="1" fill="#0f172a" />
        <!-- Nose -->
        <ellipse cx="50" cy="61" rx="4" ry="3" fill="#0f172a" />
        <!-- Mouth -->
        <path d="M46 65 Q50 68 54 65" stroke="#0f172a" stroke-width="2" stroke-linecap="round" fill="none" />
        <!-- Cheeks -->
        <circle cx="31" cy="62" r="4.5" fill="#fb7185" opacity="0.5" />
        <circle cx="69" cy="62" r="4.5" fill="#fb7185" opacity="0.5" />
      </svg>
    `),
  },
  {
    id: 'astro-pup',
    name: 'Astro Pup',
    category: 'Characters',
    svgDataUrl: createSvgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <defs>
          <linearGradient id="bg_pup" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#4f46e5" />
            <stop offset="100%" stop-color="#818cf8" />
          </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="50" fill="url(#bg_pup)" />
        <!-- Helmet Rim -->
        <circle cx="50" cy="52" r="36" fill="rgba(255,255,255,0.18)" stroke="#e0e7ff" stroke-width="2.5" />
        <!-- Floppy Ears -->
        <ellipse cx="27" cy="42" rx="7" ry="14" transform="rotate(-15 27 42)" fill="#d97706" />
        <ellipse cx="73" cy="42" rx="7" ry="14" transform="rotate(15 73 42)" fill="#d97706" />
        <!-- Pup Face -->
        <circle cx="50" cy="52" r="23" fill="#fef3c7" stroke="#78350f" stroke-width="2" />
        <!-- Eye Patch -->
        <ellipse cx="42" cy="48" rx="8" ry="9" fill="#fde68a" />
        <!-- Eyes -->
        <circle cx="43" cy="49" r="3.5" fill="#78350f" />
        <circle cx="44" cy="48" r="1.2" fill="#ffffff" />
        <circle cx="58" cy="49" r="3.5" fill="#78350f" />
        <circle cx="59" cy="48" r="1.2" fill="#ffffff" />
        <!-- Snout -->
        <ellipse cx="50" cy="58" rx="7" ry="5" fill="#ffffff" />
        <ellipse cx="50" cy="56.5" rx="3" ry="2" fill="#78350f" />
        <path d="M48 59 Q50 61 52 59" stroke="#78350f" stroke-width="1.8" stroke-linecap="round" fill="none" />
      </svg>
    `),
  },
  {
    id: 'arcane-wizard',
    name: 'Arcane Wizard',
    category: 'Fantasy',
    svgDataUrl: createSvgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <defs>
          <linearGradient id="bg_wiz" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#1e1b4b" />
            <stop offset="100%" stop-color="#4338ca" />
          </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="50" fill="url(#bg_wiz)" />
        <!-- Beard -->
        <path d="M34 56 C34 76 66 76 66 56 Z" fill="#e2e8f0" stroke="#0f172a" stroke-width="2" />
        <!-- Face -->
        <circle cx="50" cy="52" r="18" fill="#fde047" opacity="0.9" />
        <!-- Glasses -->
        <circle cx="43" cy="50" r="5.5" fill="none" stroke="#f59e0b" stroke-width="2" />
        <circle cx="57" cy="50" r="5.5" fill="none" stroke="#f59e0b" stroke-width="2" />
        <line x1="48.5" y1="50" x2="51.5" y2="50" stroke="#f59e0b" stroke-width="2" />
        <circle cx="43" cy="50" r="2" fill="#0f172a" />
        <circle cx="57" cy="50" r="2" fill="#0f172a" />
        <!-- Wizard Hat -->
        <path d="M16 44 Q50 38 84 44 Q50 41 16 44 Z" fill="#8b5cf6" stroke="#4c1d95" stroke-width="2" />
        <polygon points="50,10 32,41 68,41" fill="#7c3aed" stroke="#4c1d95" stroke-width="2" />
        <polygon points="50,22 52,26 56,26 53,29 54,33 50,30 46,33 47,29 44,26 48,26" fill="#facc15" />
      </svg>
    `),
  },
  {
    id: 'synth-gamer',
    name: 'Pixel Gamer',
    category: 'Characters',
    svgDataUrl: createSvgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <defs>
          <linearGradient id="bg_game" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#db2777" />
            <stop offset="100%" stop-color="#f43f5e" />
          </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="50" fill="url(#bg_game)" />
        <!-- Headband of Headset -->
        <path d="M26 46 C26 24 74 24 74 46" stroke="#0f172a" stroke-width="6" stroke-linecap="round" fill="none" />
        <!-- Head -->
        <circle cx="50" cy="52" r="23" fill="#fed7aa" stroke="#0f172a" stroke-width="2.5" />
        <!-- Cool Hair -->
        <path d="M30 44 Q50 28 68 38 Q56 34 40 43" fill="#1e1b4b" />
        <!-- Futuristic Visor -->
        <rect x="32" y="44" width="36" height="13" rx="4" fill="#06b6d4" stroke="#0f172a" stroke-width="2" />
        <line x1="36" y1="50" x2="64" y2="50" stroke="#a5f3fc" stroke-width="2" stroke-linecap="round" />
        <!-- Headset Earcups -->
        <rect x="22" y="42" width="8" height="18" rx="4" fill="#facc15" stroke="#0f172a" stroke-width="2" />
        <rect x="70" y="42" width="8" height="18" rx="4" fill="#facc15" stroke="#0f172a" stroke-width="2" />
        <!-- Smile -->
        <path d="M45 64 Q50 68 55 64" stroke="#0f172a" stroke-width="2.5" stroke-linecap="round" fill="none" />
      </svg>
    `),
  },
  {
    id: 'glitch-monster',
    name: 'Glitchy Alien',
    category: 'Fantasy',
    svgDataUrl: createSvgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <defs>
          <linearGradient id="bg_alien" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#7c3aed" />
            <stop offset="100%" stop-color="#a855f7" />
          </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="50" fill="url(#bg_alien)" />
        <!-- Horns -->
        <path d="M32 34 Q24 20 30 18 Q36 26 38 32" fill="#ec4899" stroke="#0f172a" stroke-width="2" />
        <path d="M68 34 Q76 20 70 18 Q64 26 62 32" fill="#ec4899" stroke="#0f172a" stroke-width="2" />
        <!-- Monster Body/Head -->
        <rect x="24" y="30" width="52" height="48" rx="20" fill="#a78bfa" stroke="#0f172a" stroke-width="2.5" />
        <!-- Big Eye -->
        <circle cx="50" cy="46" r="14" fill="#ffffff" stroke="#0f172a" stroke-width="2" />
        <circle cx="50" cy="46" r="7" fill="#0f172a" />
        <circle cx="52" cy="44" r="2.5" fill="#38bdf8" />
        <circle cx="53" cy="43" r="1" fill="#ffffff" />
        <!-- Big Happy Mouth with One Tooth -->
        <path d="M38 63 Q50 72 62 63" stroke="#0f172a" stroke-width="2.5" fill="#f43f5e" />
        <rect x="47" y="62" width="6" height="5" rx="1.5" fill="#ffffff" stroke="#0f172a" stroke-width="1.5" />
      </svg>
    `),
  },
];

/**
 * Resize and compress user-selected image to a clean 256x256 base64 JPEG/PNG data URL
 */
export async function resizeImageFile(file: File, maxSize = 256): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('Failed to read image file.'));
    reader.onload = () => {
      const img = new Image();
      img.onerror = () => reject(new Error('Invalid image file format.'));
      img.onload = () => {
        const canvas = document.createElement('canvas');
        let width = img.width;
        let height = img.height;

        // Calculate aspect-preserving crop or fit
        if (width > height) {
          if (width > maxSize) {
            height = Math.round((height * maxSize) / width);
            width = maxSize;
          }
        } else {
          if (height > maxSize) {
            width = Math.round((width * maxSize) / height);
            height = maxSize;
          }
        }

        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          resolve(reader.result as string);
          return;
        }

        ctx.drawImage(img, 0, 0, width, height);
        // Export as clean JPEG data URL
        const dataUrl = canvas.toDataURL('image/jpeg', 0.88);
        resolve(dataUrl);
      };
      img.src = reader.result as string;
    };
    reader.readAsDataURL(file);
  });
}
