from pathlib import Path
import re

root = Path(__file__).parent
route = (root / "service/app/routes/public.py").read_text()
template = (root / "service/app/assets/public-home.html").read_text()
assert 'public-home.html' in route
assert 'def mago_hero' in route
assert 'mago-hero-20260826.png' in route
assert 'mago-logo-192.png' in route
assert 'mago-favicon.png' in route
assert 'mago-cta-human-20260826.png' in route
assert 'src="/mago-hero.png"' in template
assert 'src="/brand-logo-ui.png"' in template
assert 'src="/mago-cta-human.png"' in template
assert 'rel="icon"' in template
assert 'data-nav-toggle' in template
assert 'aria-expanded="false"' in template
assert '@media (max-width: 780px)' in template
assert '@media (max-width: 480px)' in template
assert 'min-height: 48px' in template
assert 'Meta Cloud API' in template
assert 'Evolution' in template
assert '360dialog' not in template.lower()
assert 'Official Meta Partner' not in template
assert '100.000+ empresas' not in template
assert re.search(r'href="/docs"', template)
assert re.search(r'href="/admin"', template)
print("public homepage contract validation passed")
