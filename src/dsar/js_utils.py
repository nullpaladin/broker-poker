"""Shared in-page JavaScript helpers (moved out of SuperScraper to keep it small).

See docs/development_reference/embedded_js_audit.md. All functions take a pydoll
tab or element; scripts that read ``this`` run against an element.
"""

import asyncio


def unwrap_js(raw):
    """pydoll's execute_script returns {'result': {'result': {'value': X}}}; some
    call paths already hand back X. Return X either way."""
    node = raw
    for _ in range(3):
        if isinstance(node, dict) and "result" in node:
            node = node["result"]
        else:
            break
    if isinstance(node, dict) and "value" in node:
        return node["value"]
    return raw if not isinstance(raw, dict) else node


async def js_eval(target, script):
    """Run ``script`` on a tab or element and return the unwrapped value.
    The script needs a top-level ``return`` (not a wrapping IIFE)."""
    return unwrap_js(await target.execute_script(script))


async def js_click(element):
    """`element.click()` in JS — bypasses overlay interception / ElementNotVisible."""
    await element.execute_script("this.click();")


async def js_check(element, checked=True, *, dispatch=("click", "change")):
    """Toggle a checkbox/radio to ``checked`` in JS.

    Tries a real ``.click()`` first (the faithful path — fires the browser's
    own trusted click/input/change and is what React onChange listens for),
    then falls back to setting ``.checked`` + dispatching ``dispatch`` events
    for custom-styled / 1x1px / visually-hidden inputs that ignore ``.click()``.
    """
    want = "true" if checked else "false"
    events = ";".join(
        f"this.dispatchEvent(new Event('{e}',{{bubbles:true}}))" for e in dispatch
    )
    await element.execute_script(
        f"if(this.checked!=={want}){{this.click();}}"
        f"if(this.checked!=={want}){{this.checked={want};{events};}}"
    )


async def js_set_value(element, value, *, blur=False):
    """Set an <input>/<textarea> value via the native prototype setter + dispatch
    input/change[/blur]. For React/Angular controlled fields where click()+type
    silently fails. ``element`` may be the input itself or a wrapper around it."""
    events = (
        "el.dispatchEvent(new Event('input',{bubbles:true}));"
        "el.dispatchEvent(new Event('change',{bubbles:true}));"
    )
    if blur:
        events += "el.dispatchEvent(new Event('blur',{bubbles:true}));"
    await element.execute_script(
        "var el=(this.tagName==='INPUT'||this.tagName==='TEXTAREA')?this:"
        "this.querySelector('input,textarea')||this;"
        "var d=Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el),'value');"
        f"if(d&&d.set){{d.set.call(el,{value!r});}}else{{el.value={value!r};}}"
        + events
    )


async def select_native_option(
    select_element, *, value=None, text=None, index=None, ci=False,
    dispatch=("input", "change"),
):
    """Select an <option> in a native <select> by value / visible text / index,
    then dispatch input+change. Replaces the ~80 hand-copied ``_select_native_option``
    helpers across the scrapers."""
    events = ";".join(
        f"this.dispatchEvent(new Event('{e}',{{bubbles:true}}))" for e in dispatch
    )
    if value is not None:
        match = "o.value.toLowerCase()===V.toLowerCase()" if ci else "o.value===V"
        body = f"var V={value!r};"
    elif text is not None:
        match = "T.toLowerCase()===V.toLowerCase()" if ci else "T===V"
        body = f"var V={text!r};"
    elif index is not None:
        await select_element.execute_script(f"this.selectedIndex={int(index)};{events};")
        return
    else:
        raise ValueError("select_native_option needs value=, text= or index=")
    await select_element.execute_script(
        body
        + "for(var i=0;i<this.options.length;i++){var o=this.options[i];"
        "var T=(o.text||o.textContent||'').trim();"
        f"if({match}){{this.selectedIndex=i;break;}}}}"
        + events + ";"
    )


async def check_termly_attestations(tab):
    """Force every Termly ``__doNotSubmit__``-prefixed attestation checkbox
    checked + dispatch. These gate submission regardless of request type."""
    await tab.execute_script(
        "document.querySelectorAll('input[name^=\"__doNotSubmit__\"]').forEach(function(cb){"
        "cb.checked=true;"
        "cb.dispatchEvent(new Event('click',{bubbles:true}));"
        "cb.dispatchEvent(new Event('change',{bubbles:true}));"
        "});"
    )


async def page_text(tab):
    """`document.body.innerText` — for post-submit confirmation checks."""
    return await js_eval(tab, "return document.body.innerText;")


async def fill_autocomplete(tab, field, value, *, option_text=None, settle=1.3):
    """OneTrust-style autocomplete combobox: clear via JS, type, then click the
    matching role=option (falling back to trusting the typed value). Returns
    True on apparent success."""
    await field.execute_script(
        "this.value='';this.dispatchEvent(new Event('input',{bubbles:true}));"
    )
    await field.click()
    await tab.keyboard.type_text(text=value)
    await asyncio.sleep(settle)
    target = option_text or value
    opt = await tab.find(
        xpath=f"//*[@role='option' and normalize-space()={target!r}]", raise_exc=False
    )
    if opt:
        await opt.click()
        return True
    current = await js_eval(field, "return this.value;")
    return bool(current)
