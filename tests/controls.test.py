"""Static control-style regression checks, not browser visual verification."""
from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]
css=(root/'styles.css').read_text()
for token,value in {'control-bg':'#f5f5f5','control-hover':'#eaeaea','control-radius':'999px','control-height':'38px','control-compact':'32px','control-mini':'30px'}.items():
    assert f'--{token}:{value}' in css, token
button=re.search(r'(?<![\w.-])button\{([^}]+)\}',css).group(1)
assert 'background:var(--control-bg)' in button
assert 'border-radius:var(--control-radius)' in button
select=re.search(r'\.select-label select,select\.zoom-control,\.compare-toolbar select\{([^}]+)\}',css).group(1)
for declaration in ['appearance:none','background-color:var(--control-bg)','background-image:var(--chevron)','border-radius:var(--control-radius)','min-height:var(--control-height)']:
    assert declaration in select, declaration
assert '.sample-label select.zoom-control{min-height:var(--control-mini);' in css
assert '.row-actions button{font-size:11px;min-height:var(--control-compact);' in css
assert '.close-button{width:var(--control-compact);height:var(--control-compact);' in css
assert 'button:disabled,button:disabled:hover' in css
assert 'button:focus-visible' in css and 'select:focus-visible' in css
assert 'grid-template-columns:repeat(3,minmax(0,1fr))' in css
assert 'background:transparent;border-radius:0;padding:0;' in css, 'Specimens must remain continuous white rows'
assert 'font-size:16px;font-weight:400' in css
assert 'width:192px;height:48px' in css
assert css.count('{')==css.count('}')
print('Control checks passed: shared gray/pill tokens, 38/32/30px hierarchy, native selects, round close, focus/disabled states, white specimens and unchanged pixel wordmark.')
