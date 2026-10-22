export function icon(name, extraClass = '') {
  const cls = extraClass ? `lucide ${extraClass}` : 'lucide';
  return `<svg class="${cls}" aria-hidden="true"><use href="#icon-${name}"></use></svg>`;
}

export async function loadIconSprite() {
  if (document.getElementById('lucide-sprite-root')) return;
  try {
    const res = await fetch('/assets/icons.svg');
    if (!res.ok) return;
    const svgText = await res.text();
    const wrap = document.createElement('div');
    wrap.id = 'lucide-sprite-root';
    wrap.style.display = 'none';
    wrap.innerHTML = svgText;
    document.body.prepend(wrap);
  } catch (e) {
    console.warn('Could not inline SVG sprite:', e);
  }
}
