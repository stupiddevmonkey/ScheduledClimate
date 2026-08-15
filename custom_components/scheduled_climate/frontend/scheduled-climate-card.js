const H = globalThis, Z = H.ShadowRoot && (H.ShadyCSS === void 0 || H.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, G = /* @__PURE__ */ Symbol(), te = /* @__PURE__ */ new WeakMap();
let _e = class {
  constructor(e, t, i) {
    if (this._$cssResult$ = !0, i !== G) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = e, this.t = t;
  }
  get styleSheet() {
    let e = this.o;
    const t = this.t;
    if (Z && e === void 0) {
      const i = t !== void 0 && t.length === 1;
      i && (e = te.get(t)), e === void 0 && ((this.o = e = new CSSStyleSheet()).replaceSync(this.cssText), i && te.set(t, e));
    }
    return e;
  }
  toString() {
    return this.cssText;
  }
};
const xe = (r) => new _e(typeof r == "string" ? r : r + "", void 0, G), ge = (r, ...e) => {
  const t = r.length === 1 ? r[0] : e.reduce((i, s, a) => i + ((o) => {
    if (o._$cssResult$ === !0) return o.cssText;
    if (typeof o == "number") return o;
    throw Error("Value passed to 'css' function must be a 'css' function result: " + o + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
  })(s) + r[a + 1], r[0]);
  return new _e(t, r, G);
}, we = (r, e) => {
  if (Z) r.adoptedStyleSheets = e.map((t) => t instanceof CSSStyleSheet ? t : t.styleSheet);
  else for (const t of e) {
    const i = document.createElement("style"), s = H.litNonce;
    s !== void 0 && i.setAttribute("nonce", s), i.textContent = t.cssText, r.appendChild(i);
  }
}, ie = Z ? (r) => r : (r) => r instanceof CSSStyleSheet ? ((e) => {
  let t = "";
  for (const i of e.cssRules) t += i.cssText;
  return xe(t);
})(r) : r;
const { is: Ae, defineProperty: Se, getOwnPropertyDescriptor: Ee, getOwnPropertyNames: ke, getOwnPropertySymbols: Ce, getPrototypeOf: Te } = Object, j = globalThis, se = j.trustedTypes, De = se ? se.emptyScript : "", Pe = j.reactiveElementPolyfillSupport, T = (r, e) => r, q = { toAttribute(r, e) {
  switch (e) {
    case Boolean:
      r = r ? De : null;
      break;
    case Object:
    case Array:
      r = r == null ? r : JSON.stringify(r);
  }
  return r;
}, fromAttribute(r, e) {
  let t = r;
  switch (e) {
    case Boolean:
      t = r !== null;
      break;
    case Number:
      t = r === null ? null : Number(r);
      break;
    case Object:
    case Array:
      try {
        t = JSON.parse(r);
      } catch {
        t = null;
      }
  }
  return t;
} }, fe = (r, e) => !Ae(r, e), re = { attribute: !0, type: String, converter: q, reflect: !1, useDefault: !1, hasChanged: fe };
Symbol.metadata ??= /* @__PURE__ */ Symbol("metadata"), j.litPropertyMetadata ??= /* @__PURE__ */ new WeakMap();
let w = class extends HTMLElement {
  static addInitializer(e) {
    this._$Ei(), (this.l ??= []).push(e);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(e, t = re) {
    if (t.state && (t.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(e) && ((t = Object.create(t)).wrapped = !0), this.elementProperties.set(e, t), !t.noAccessor) {
      const i = /* @__PURE__ */ Symbol(), s = this.getPropertyDescriptor(e, i, t);
      s !== void 0 && Se(this.prototype, e, s);
    }
  }
  static getPropertyDescriptor(e, t, i) {
    const { get: s, set: a } = Ee(this.prototype, e) ?? { get() {
      return this[t];
    }, set(o) {
      this[t] = o;
    } };
    return { get: s, set(o) {
      const n = s?.call(this);
      a?.call(this, o), this.requestUpdate(e, n, i);
    }, configurable: !0, enumerable: !0 };
  }
  static getPropertyOptions(e) {
    return this.elementProperties.get(e) ?? re;
  }
  static _$Ei() {
    if (this.hasOwnProperty(T("elementProperties"))) return;
    const e = Te(this);
    e.finalize(), e.l !== void 0 && (this.l = [...e.l]), this.elementProperties = new Map(e.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(T("finalized"))) return;
    if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(T("properties"))) {
      const t = this.properties, i = [...ke(t), ...Ce(t)];
      for (const s of i) this.createProperty(s, t[s]);
    }
    const e = this[Symbol.metadata];
    if (e !== null) {
      const t = litPropertyMetadata.get(e);
      if (t !== void 0) for (const [i, s] of t) this.elementProperties.set(i, s);
    }
    this._$Eh = /* @__PURE__ */ new Map();
    for (const [t, i] of this.elementProperties) {
      const s = this._$Eu(t, i);
      s !== void 0 && this._$Eh.set(s, t);
    }
    this.elementStyles = this.finalizeStyles(this.styles);
  }
  static finalizeStyles(e) {
    const t = [];
    if (Array.isArray(e)) {
      const i = new Set(e.flat(1 / 0).reverse());
      for (const s of i) t.unshift(ie(s));
    } else e !== void 0 && t.push(ie(e));
    return t;
  }
  static _$Eu(e, t) {
    const i = t.attribute;
    return i === !1 ? void 0 : typeof i == "string" ? i : typeof e == "string" ? e.toLowerCase() : void 0;
  }
  constructor() {
    super(), this._$Ep = void 0, this.isUpdatePending = !1, this.hasUpdated = !1, this._$Em = null, this._$Ev();
  }
  _$Ev() {
    this._$ES = new Promise((e) => this.enableUpdating = e), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), this.constructor.l?.forEach((e) => e(this));
  }
  addController(e) {
    (this._$EO ??= /* @__PURE__ */ new Set()).add(e), this.renderRoot !== void 0 && this.isConnected && e.hostConnected?.();
  }
  removeController(e) {
    this._$EO?.delete(e);
  }
  _$E_() {
    const e = /* @__PURE__ */ new Map(), t = this.constructor.elementProperties;
    for (const i of t.keys()) this.hasOwnProperty(i) && (e.set(i, this[i]), delete this[i]);
    e.size > 0 && (this._$Ep = e);
  }
  createRenderRoot() {
    const e = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
    return we(e, this.constructor.elementStyles), e;
  }
  connectedCallback() {
    this.renderRoot ??= this.createRenderRoot(), this.enableUpdating(!0), this._$EO?.forEach((e) => e.hostConnected?.());
  }
  enableUpdating(e) {
  }
  disconnectedCallback() {
    this._$EO?.forEach((e) => e.hostDisconnected?.());
  }
  attributeChangedCallback(e, t, i) {
    this._$AK(e, i);
  }
  _$ET(e, t) {
    const i = this.constructor.elementProperties.get(e), s = this.constructor._$Eu(e, i);
    if (s !== void 0 && i.reflect === !0) {
      const a = (i.converter?.toAttribute !== void 0 ? i.converter : q).toAttribute(t, i.type);
      this._$Em = e, a == null ? this.removeAttribute(s) : this.setAttribute(s, a), this._$Em = null;
    }
  }
  _$AK(e, t) {
    const i = this.constructor, s = i._$Eh.get(e);
    if (s !== void 0 && this._$Em !== s) {
      const a = i.getPropertyOptions(s), o = typeof a.converter == "function" ? { fromAttribute: a.converter } : a.converter?.fromAttribute !== void 0 ? a.converter : q;
      this._$Em = s;
      const n = o.fromAttribute(t, a.type);
      this[s] = n ?? this._$Ej?.get(s) ?? n, this._$Em = null;
    }
  }
  requestUpdate(e, t, i, s = !1, a) {
    if (e !== void 0) {
      const o = this.constructor;
      if (s === !1 && (a = this[e]), i ??= o.getPropertyOptions(e), !((i.hasChanged ?? fe)(a, t) || i.useDefault && i.reflect && a === this._$Ej?.get(e) && !this.hasAttribute(o._$Eu(e, i)))) return;
      this.C(e, t, i);
    }
    this.isUpdatePending === !1 && (this._$ES = this._$EP());
  }
  C(e, t, { useDefault: i, reflect: s, wrapped: a }, o) {
    i && !(this._$Ej ??= /* @__PURE__ */ new Map()).has(e) && (this._$Ej.set(e, o ?? t ?? this[e]), a !== !0 || o !== void 0) || (this._$AL.has(e) || (this.hasUpdated || i || (t = void 0), this._$AL.set(e, t)), s === !0 && this._$Em !== e && (this._$Eq ??= /* @__PURE__ */ new Set()).add(e));
  }
  async _$EP() {
    this.isUpdatePending = !0;
    try {
      await this._$ES;
    } catch (t) {
      Promise.reject(t);
    }
    const e = this.scheduleUpdate();
    return e != null && await e, !this.isUpdatePending;
  }
  scheduleUpdate() {
    return this.performUpdate();
  }
  performUpdate() {
    if (!this.isUpdatePending) return;
    if (!this.hasUpdated) {
      if (this.renderRoot ??= this.createRenderRoot(), this._$Ep) {
        for (const [s, a] of this._$Ep) this[s] = a;
        this._$Ep = void 0;
      }
      const i = this.constructor.elementProperties;
      if (i.size > 0) for (const [s, a] of i) {
        const { wrapped: o } = a, n = this[s];
        o !== !0 || this._$AL.has(s) || n === void 0 || this.C(s, void 0, a, n);
      }
    }
    let e = !1;
    const t = this._$AL;
    try {
      e = this.shouldUpdate(t), e ? (this.willUpdate(t), this._$EO?.forEach((i) => i.hostUpdate?.()), this.update(t)) : this._$EM();
    } catch (i) {
      throw e = !1, this._$EM(), i;
    }
    e && this._$AE(t);
  }
  willUpdate(e) {
  }
  _$AE(e) {
    this._$EO?.forEach((t) => t.hostUpdated?.()), this.hasUpdated || (this.hasUpdated = !0, this.firstUpdated(e)), this.updated(e);
  }
  _$EM() {
    this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = !1;
  }
  get updateComplete() {
    return this.getUpdateComplete();
  }
  getUpdateComplete() {
    return this._$ES;
  }
  shouldUpdate(e) {
    return !0;
  }
  update(e) {
    this._$Eq &&= this._$Eq.forEach((t) => this._$ET(t, this[t])), this._$EM();
  }
  updated(e) {
  }
  firstUpdated(e) {
  }
};
w.elementStyles = [], w.shadowRootOptions = { mode: "open" }, w[T("elementProperties")] = /* @__PURE__ */ new Map(), w[T("finalized")] = /* @__PURE__ */ new Map(), Pe?.({ ReactiveElement: w }), (j.reactiveElementVersions ??= []).push("2.1.2");
const Q = globalThis, ae = (r) => r, L = Q.trustedTypes, oe = L ? L.createPolicy("lit-html", { createHTML: (r) => r }) : void 0, be = "$lit$", b = `lit$${Math.random().toFixed(9).slice(2)}$`, $e = "?" + b, Me = `<${$e}>`, x = document, P = () => x.createComment(""), M = (r) => r === null || typeof r != "object" && typeof r != "function", X = Array.isArray, Ue = (r) => X(r) || typeof r?.[Symbol.iterator] == "function", W = `[ 	
\f\r]`, C = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, ne = /-->/g, le = />/g, $ = RegExp(`>|${W}(?:([^\\s"'>=/]+)(${W}*=${W}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g"), ce = /'/g, de = /"/g, ye = /^(?:script|style|textarea|title)$/i, ze = (r) => (e, ...t) => ({ _$litType$: r, strings: e, values: t }), l = ze(1), E = /* @__PURE__ */ Symbol.for("lit-noChange"), d = /* @__PURE__ */ Symbol.for("lit-nothing"), he = /* @__PURE__ */ new WeakMap(), y = x.createTreeWalker(x, 129);
function ve(r, e) {
  if (!X(r) || !r.hasOwnProperty("raw")) throw Error("invalid template strings array");
  return oe !== void 0 ? oe.createHTML(e) : e;
}
const Ne = (r, e) => {
  const t = r.length - 1, i = [];
  let s, a = e === 2 ? "<svg>" : e === 3 ? "<math>" : "", o = C;
  for (let n = 0; n < t; n++) {
    const c = r[n];
    let p, h, u = -1, _ = 0;
    for (; _ < c.length && (o.lastIndex = _, h = o.exec(c), h !== null); ) _ = o.lastIndex, o === C ? h[1] === "!--" ? o = ne : h[1] !== void 0 ? o = le : h[2] !== void 0 ? (ye.test(h[2]) && (s = RegExp("</" + h[2], "g")), o = $) : h[3] !== void 0 && (o = $) : o === $ ? h[0] === ">" ? (o = s ?? C, u = -1) : h[1] === void 0 ? u = -2 : (u = o.lastIndex - h[2].length, p = h[1], o = h[3] === void 0 ? $ : h[3] === '"' ? de : ce) : o === de || o === ce ? o = $ : o === ne || o === le ? o = C : (o = $, s = void 0);
    const f = o === $ && r[n + 1].startsWith("/>") ? " " : "";
    a += o === C ? c + Me : u >= 0 ? (i.push(p), c.slice(0, u) + be + c.slice(u) + b + f) : c + b + (u === -2 ? n : f);
  }
  return [ve(r, a + (r[t] || "<?>") + (e === 2 ? "</svg>" : e === 3 ? "</math>" : "")), i];
};
class U {
  constructor({ strings: e, _$litType$: t }, i) {
    let s;
    this.parts = [];
    let a = 0, o = 0;
    const n = e.length - 1, c = this.parts, [p, h] = Ne(e, t);
    if (this.el = U.createElement(p, i), y.currentNode = this.el.content, t === 2 || t === 3) {
      const u = this.el.content.firstChild;
      u.replaceWith(...u.childNodes);
    }
    for (; (s = y.nextNode()) !== null && c.length < n; ) {
      if (s.nodeType === 1) {
        if (s.hasAttributes()) for (const u of s.getAttributeNames()) if (u.endsWith(be)) {
          const _ = h[o++], f = s.getAttribute(u).split(b), N = /([.?@])?(.*)/.exec(_);
          c.push({ type: 1, index: a, name: N[2], strings: f, ctor: N[1] === "." ? Oe : N[1] === "?" ? Le : N[1] === "@" ? Re : V }), s.removeAttribute(u);
        } else u.startsWith(b) && (c.push({ type: 6, index: a }), s.removeAttribute(u));
        if (ye.test(s.tagName)) {
          const u = s.textContent.split(b), _ = u.length - 1;
          if (_ > 0) {
            s.textContent = L ? L.emptyScript : "";
            for (let f = 0; f < _; f++) s.append(u[f], P()), y.nextNode(), c.push({ type: 2, index: ++a });
            s.append(u[_], P());
          }
        }
      } else if (s.nodeType === 8) if (s.data === $e) c.push({ type: 2, index: a });
      else {
        let u = -1;
        for (; (u = s.data.indexOf(b, u + 1)) !== -1; ) c.push({ type: 7, index: a }), u += b.length - 1;
      }
      a++;
    }
  }
  static createElement(e, t) {
    const i = x.createElement("template");
    return i.innerHTML = e, i;
  }
}
function k(r, e, t = r, i) {
  if (e === E) return e;
  let s = i !== void 0 ? t._$Co?.[i] : t._$Cl;
  const a = M(e) ? void 0 : e._$litDirective$;
  return s?.constructor !== a && (s?._$AO?.(!1), a === void 0 ? s = void 0 : (s = new a(r), s._$AT(r, t, i)), i !== void 0 ? (t._$Co ??= [])[i] = s : t._$Cl = s), s !== void 0 && (e = k(r, s._$AS(r, e.values), s, i)), e;
}
class He {
  constructor(e, t) {
    this._$AV = [], this._$AN = void 0, this._$AD = e, this._$AM = t;
  }
  get parentNode() {
    return this._$AM.parentNode;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  u(e) {
    const { el: { content: t }, parts: i } = this._$AD, s = (e?.creationScope ?? x).importNode(t, !0);
    y.currentNode = s;
    let a = y.nextNode(), o = 0, n = 0, c = i[0];
    for (; c !== void 0; ) {
      if (o === c.index) {
        let p;
        c.type === 2 ? p = new z(a, a.nextSibling, this, e) : c.type === 1 ? p = new c.ctor(a, c.name, c.strings, this, e) : c.type === 6 && (p = new Be(a, this, e)), this._$AV.push(p), c = i[++n];
      }
      o !== c?.index && (a = y.nextNode(), o++);
    }
    return y.currentNode = x, s;
  }
  p(e) {
    let t = 0;
    for (const i of this._$AV) i !== void 0 && (i.strings !== void 0 ? (i._$AI(e, i, t), t += i.strings.length - 2) : i._$AI(e[t])), t++;
  }
}
class z {
  get _$AU() {
    return this._$AM?._$AU ?? this._$Cv;
  }
  constructor(e, t, i, s) {
    this.type = 2, this._$AH = d, this._$AN = void 0, this._$AA = e, this._$AB = t, this._$AM = i, this.options = s, this._$Cv = s?.isConnected ?? !0;
  }
  get parentNode() {
    let e = this._$AA.parentNode;
    const t = this._$AM;
    return t !== void 0 && e?.nodeType === 11 && (e = t.parentNode), e;
  }
  get startNode() {
    return this._$AA;
  }
  get endNode() {
    return this._$AB;
  }
  _$AI(e, t = this) {
    e = k(this, e, t), M(e) ? e === d || e == null || e === "" ? (this._$AH !== d && this._$AR(), this._$AH = d) : e !== this._$AH && e !== E && this._(e) : e._$litType$ !== void 0 ? this.$(e) : e.nodeType !== void 0 ? this.T(e) : Ue(e) ? this.k(e) : this._(e);
  }
  O(e) {
    return this._$AA.parentNode.insertBefore(e, this._$AB);
  }
  T(e) {
    this._$AH !== e && (this._$AR(), this._$AH = this.O(e));
  }
  _(e) {
    this._$AH !== d && M(this._$AH) ? this._$AA.nextSibling.data = e : this.T(x.createTextNode(e)), this._$AH = e;
  }
  $(e) {
    const { values: t, _$litType$: i } = e, s = typeof i == "number" ? this._$AC(e) : (i.el === void 0 && (i.el = U.createElement(ve(i.h, i.h[0]), this.options)), i);
    if (this._$AH?._$AD === s) this._$AH.p(t);
    else {
      const a = new He(s, this), o = a.u(this.options);
      a.p(t), this.T(o), this._$AH = a;
    }
  }
  _$AC(e) {
    let t = he.get(e.strings);
    return t === void 0 && he.set(e.strings, t = new U(e)), t;
  }
  k(e) {
    X(this._$AH) || (this._$AH = [], this._$AR());
    const t = this._$AH;
    let i, s = 0;
    for (const a of e) s === t.length ? t.push(i = new z(this.O(P()), this.O(P()), this, this.options)) : i = t[s], i._$AI(a), s++;
    s < t.length && (this._$AR(i && i._$AB.nextSibling, s), t.length = s);
  }
  _$AR(e = this._$AA.nextSibling, t) {
    for (this._$AP?.(!1, !0, t); e !== this._$AB; ) {
      const i = ae(e).nextSibling;
      ae(e).remove(), e = i;
    }
  }
  setConnected(e) {
    this._$AM === void 0 && (this._$Cv = e, this._$AP?.(e));
  }
}
class V {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(e, t, i, s, a) {
    this.type = 1, this._$AH = d, this._$AN = void 0, this.element = e, this.name = t, this._$AM = s, this.options = a, i.length > 2 || i[0] !== "" || i[1] !== "" ? (this._$AH = Array(i.length - 1).fill(new String()), this.strings = i) : this._$AH = d;
  }
  _$AI(e, t = this, i, s) {
    const a = this.strings;
    let o = !1;
    if (a === void 0) e = k(this, e, t, 0), o = !M(e) || e !== this._$AH && e !== E, o && (this._$AH = e);
    else {
      const n = e;
      let c, p;
      for (e = a[0], c = 0; c < a.length - 1; c++) p = k(this, n[i + c], t, c), p === E && (p = this._$AH[c]), o ||= !M(p) || p !== this._$AH[c], p === d ? e = d : e !== d && (e += (p ?? "") + a[c + 1]), this._$AH[c] = p;
    }
    o && !s && this.j(e);
  }
  j(e) {
    e === d ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, e ?? "");
  }
}
class Oe extends V {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(e) {
    this.element[this.name] = e === d ? void 0 : e;
  }
}
class Le extends V {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(e) {
    this.element.toggleAttribute(this.name, !!e && e !== d);
  }
}
class Re extends V {
  constructor(e, t, i, s, a) {
    super(e, t, i, s, a), this.type = 5;
  }
  _$AI(e, t = this) {
    if ((e = k(this, e, t, 0) ?? d) === E) return;
    const i = this._$AH, s = e === d && i !== d || e.capture !== i.capture || e.once !== i.once || e.passive !== i.passive, a = e !== d && (i === d || s);
    s && this.element.removeEventListener(this.name, this, i), a && this.element.addEventListener(this.name, this, e), this._$AH = e;
  }
  handleEvent(e) {
    typeof this._$AH == "function" ? this._$AH.call(this.options?.host ?? this.element, e) : this._$AH.handleEvent(e);
  }
}
class Be {
  constructor(e, t, i) {
    this.element = e, this.type = 6, this._$AN = void 0, this._$AM = t, this.options = i;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(e) {
    k(this, e);
  }
}
const Ie = Q.litHtmlPolyfillSupport;
Ie?.(U, z), (Q.litHtmlVersions ??= []).push("3.3.3");
const je = (r, e, t) => {
  const i = t?.renderBefore ?? e;
  let s = i._$litPart$;
  if (s === void 0) {
    const a = t?.renderBefore ?? null;
    i._$litPart$ = s = new z(e.insertBefore(P(), a), a, void 0, t ?? {});
  }
  return s._$AI(r), s;
};
const ee = globalThis;
class A extends w {
  constructor() {
    super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
  }
  createRenderRoot() {
    const e = super.createRenderRoot();
    return this.renderOptions.renderBefore ??= e.firstChild, e;
  }
  update(e) {
    const t = this.render();
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(e), this._$Do = je(t, this.renderRoot, this.renderOptions);
  }
  connectedCallback() {
    super.connectedCallback(), this._$Do?.setConnected(!0);
  }
  disconnectedCallback() {
    super.disconnectedCallback(), this._$Do?.setConnected(!1);
  }
  render() {
    return E;
  }
}
A._$litElement$ = !0, A.finalized = !0, ee.litElementHydrateSupport?.({ LitElement: A });
const Ve = ee.litElementPolyfillSupport;
Ve?.({ LitElement: A });
(ee.litElementVersions ??= []).push("4.2.2");
const S = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday"
], D = [15, 30, 60, 120], O = {
  monday: "Mon",
  tuesday: "Tue",
  wednesday: "Wed",
  thursday: "Thu",
  friday: "Fri",
  saturday: "Sat",
  sunday: "Sun"
};
function ue(r = /* @__PURE__ */ new Date()) {
  return S[(r.getDay() + 6) % 7];
}
function We() {
  return {
    index: null,
    from: "07:00",
    to: "22:00",
    hvac_mode: "",
    temperature: "",
    target_temp_low: "",
    target_temp_high: "",
    fan_mode: "",
    humidity: ""
  };
}
function m(r) {
  return r.slice(0, 5);
}
function g(r, e = !1) {
  const [t, i] = m(r).split(":").map(Number), s = t * 60 + i;
  return e && s === 0 ? 1440 : s;
}
function K(r, e = !1) {
  return e && g(r, !0) === 1440 ? "24:00:00" : `${m(r)}:00`;
}
function v(r) {
  if (r.trim() === "") return;
  const e = Number(r);
  return Number.isFinite(e) ? e : void 0;
}
function pe(r) {
  const e = {};
  r.hvac_mode && (e.hvac_mode = r.hvac_mode), r.fan_mode && (e.fan_mode = r.fan_mode);
  const t = v(r.temperature);
  t !== void 0 && (e.temperature = t);
  const i = v(r.target_temp_low), s = v(r.target_temp_high);
  i !== void 0 && (e.target_temp_low = i), s !== void 0 && (e.target_temp_high = s);
  const a = v(r.humidity);
  a !== void 0 && (e.humidity = a);
  const o = {
    from: K(r.from),
    to: K(r.to, !0)
  };
  return Object.keys(e).length > 0 && (o.data = e), o;
}
function me(r, e) {
  const t = r.data ?? {}, i = (s) => t[s] === void 0 ? "" : String(t[s]);
  return {
    index: e,
    from: m(r.from),
    to: m(r.to) === "24:00" ? "00:00" : m(r.to),
    hvac_mode: i("hvac_mode"),
    temperature: i("temperature"),
    target_temp_low: i("target_temp_low"),
    target_temp_high: i("target_temp_high"),
    fan_mode: i("fan_mode"),
    humidity: i("humidity")
  };
}
function Fe(r, e) {
  if (!r.from || !r.to) return "Set a start and end time";
  const t = g(r.from), i = g(r.to, !0);
  if (i <= t) return "The end time must be after the start time";
  const s = v(r.target_temp_low), a = v(r.target_temp_high);
  return s === void 0 != (a === void 0) ? "A temperature range needs both a low and a high value" : s !== void 0 && a !== void 0 && s >= a ? "The low temperature must be below the high temperature" : v(r.temperature) !== void 0 && s !== void 0 ? "Set either a target temperature or a temperature range" : e.some((n, c) => c === r.index ? !1 : t < g(n.to, !0) && i > g(n.from)) ? "This block overlaps another block on the same day" : null;
}
function R(r) {
  return [...r].sort((e, t) => g(e.from) - g(t.from));
}
function F(r, e, t) {
  return { ...r, [e]: R(t) };
}
function qe(r) {
  const e = {
    type: "schedule/update",
    schedule_id: r.id,
    name: r.name
  };
  r.icon && (e.icon = r.icon);
  for (const t of S)
    e[t] = R(r[t] ?? []);
  return e;
}
function Ke(r) {
  const e = r.data ?? {}, t = [];
  return e.hvac_mode !== void 0 && t.push(String(e.hvac_mode).replaceAll("_", " ")), e.temperature !== void 0 && t.push(`${e.temperature}°`), e.target_temp_low !== void 0 && e.target_temp_high !== void 0 && t.push(`${e.target_temp_low}° – ${e.target_temp_high}°`), e.fan_mode !== void 0 && t.push(`fan ${e.fan_mode}`), e.humidity !== void 0 && t.push(`${e.humidity}%`), t.length > 0 ? t.join(" · ") : "No changes";
}
function Je(r) {
  const e = r?.on_time ? m(r.on_time) : "07:00", t = r?.off_time ? m(r.off_time) : "22:00";
  return g(t, !0) <= g(e) ? [] : [{ from: `${e}:00`, to: K(t, !0) }];
}
const B = class B extends A {
  setConfig(e) {
    this._config = { ...e };
  }
  _setValue(e, t) {
    if (!this._config) return;
    const i = { ...this._config, [e]: t };
    this._config = i, this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: i },
        bubbles: !0,
        composed: !0
      })
    );
  }
  render() {
    if (!this.hass || !this._config) return d;
    const e = Object.values(this.hass.states).filter(
      (i) => i.entity_id.startsWith("climate.") && "schedule_enabled" in i.attributes
    ), t = (this._config.timer_presets ?? D).join(", ");
    return l`
      <div class="form">
        <label>
          Entity
          <select
            .value=${this._config.entity ?? ""}
            @change=${(i) => this._setValue("entity", i.target.value)}
          >
            <option value="" disabled>Select an entity</option>
            ${e.map(
      (i) => l`
                <option value=${i.entity_id}>
                  ${i.attributes.friendly_name ?? i.entity_id}
                </option>
              `
    )}
          </select>
        </label>
        <label>
          Card name
          <input
            type="text"
            .value=${this._config.name ?? ""}
            @input=${(i) => this._setValue("name", i.target.value)}
          />
        </label>
        <label>
          Layout
          <select
            name="layout"
            .value=${this._config.layout ?? "standard"}
            @change=${(i) => this._setValue(
      "layout",
      i.target.value
    )}
          >
            <option value="standard">Standard</option>
            <option value="compact">Compact</option>
          </select>
        </label>
        <label class="toggle">
          <input
            type="checkbox"
            .checked=${this._config.show_schedule !== !1}
            @change=${(i) => this._setValue(
      "show_schedule",
      i.target.checked
    )}
          />
          Show schedule controls
        </label>
        <label class="toggle">
          <input
            type="checkbox"
            .checked=${this._config.schedule_editable !== !1}
            @change=${(i) => this._setValue(
      "schedule_editable",
      i.target.checked
    )}
          />
          Allow editing the schedule
        </label>
        <label>
          Day shown first
          <select
            name="default_schedule_day"
            .value=${this._config.default_schedule_day ?? ""}
            @change=${(i) => this._setValue(
      "default_schedule_day",
      i.target.value || void 0
    )}
          >
            <option value="">Today</option>
            ${S.map(
      (i) => l`<option value=${i}>${O[i]}</option>`
    )}
          </select>
        </label>
        <label class="toggle">
          <input
            type="checkbox"
            .checked=${this._config.show_timer !== !1}
            @change=${(i) => this._setValue(
      "show_timer",
      i.target.checked
    )}
          />
          Show timer controls
        </label>
        <label>
          Timer presets (minutes)
          <input
            type="text"
            .value=${t}
            @change=${(i) => {
      const s = i.target.value.split(",").map((a) => Number.parseInt(a.trim(), 10)).filter((a) => Number.isFinite(a) && a > 0);
      this._setValue("timer_presets", s.length ? s : D);
    }}
          />
        </label>
      </div>
    `;
  }
};
B.properties = {
  hass: { attribute: !1 },
  _config: { state: !0 }
}, B.styles = ge`
    :host { display: block; }
    .form { display: grid; gap: 16px; padding: 8px 0; }
    label { display: grid; gap: 6px; color: var(--primary-text-color); }
    .toggle { display: flex; align-items: center; gap: 10px; }
    input[type="checkbox"] { accent-color: var(--primary-color); }
    select, input[type="text"] {
      box-sizing: border-box;
      width: 100%;
      min-height: 42px;
      padding: 8px 10px;
      color: var(--primary-text-color);
      background: var(--card-background-color);
      border: 1px solid var(--divider-color);
      border-radius: 4px;
      font: inherit;
    }
  `;
let J = B;
customElements.get("scheduled-climate-card-editor") || customElements.define("scheduled-climate-card-editor", J);
const Ye = /* @__PURE__ */ new Set(["unavailable", "unknown"]), Ze = "scheduled-climate-card:collapsed", I = class I extends A {
  constructor() {
    super(...arguments), this._busy = !1, this._message = "", this._timerMinutes = 30, this._selectedDay = ue(), this._scheduleError = "", this._loadedScheduleId = "", this._collapsed = {
      preset: !1,
      schedule: !1,
      timer: !1
    };
  }
  static getConfigElement() {
    return document.createElement("scheduled-climate-card-editor");
  }
  static getStubConfig() {
    return {
      type: "custom:scheduled-climate-card",
      entity: "",
      layout: "standard",
      show_schedule: !0,
      show_timer: !0,
      schedule_editable: !0,
      timer_presets: D
    };
  }
  setConfig(e) {
    if (!e.entity) throw new Error("Scheduled Climate Card requires an entity");
    this._config = {
      layout: "standard",
      show_schedule: !0,
      show_timer: !0,
      schedule_editable: !0,
      timer_presets: D,
      ...e
    }, this._selectedDay = this._config.default_schedule_day ?? ue(), this._collapsed = this._loadCollapseState(e.entity);
  }
  getCardSize() {
    return 7;
  }
  disconnectedCallback() {
    super.disconnectedCallback(), this._unsubscribeSchedules?.(), this._unsubscribeSchedules = void 0, this._loadedScheduleId = "";
  }
  willUpdate() {
    const e = this._state?.attributes.schedule_id ?? "";
    e !== this._loadedScheduleId && (this._loadedScheduleId = e, this._schedule = void 0, this._draft = void 0, e && this._subscribeSchedules());
  }
  get _isAdmin() {
    return this.hass?.user?.is_admin === !0;
  }
  get _canEditSchedule() {
    return this._isAdmin && this._config?.schedule_editable !== !1;
  }
  async _subscribeSchedules() {
    if (this._unsubscribeSchedules?.(), this._unsubscribeSchedules = void 0, await this._loadSchedules(), !!this.hass?.connection)
      try {
        this._unsubscribeSchedules = await this.hass.connection.subscribeMessage(
          () => {
            this._loadSchedules();
          },
          { type: "schedule/subscribe" }
        );
      } catch {
      }
  }
  async _loadSchedules() {
    const e = this._state?.attributes.schedule_id;
    if (!(!this.hass || !e))
      try {
        const t = await this.hass.callWS({
          type: "schedule/list"
        });
        this._schedule = t.find((i) => i.id === e);
      } catch (t) {
        this._scheduleError = t instanceof Error ? t.message : "Unable to load the schedule";
      }
  }
  get _state() {
    return this._config && this.hass?.states[this._config.entity];
  }
  _storageKey(e) {
    return `${Ze}:${e}`;
  }
  _loadCollapseState(e) {
    const t = {
      preset: !1,
      schedule: !1,
      timer: !1
    };
    try {
      const i = localStorage.getItem(this._storageKey(e));
      if (!i) return t;
      const s = JSON.parse(i);
      return {
        preset: s.preset === !0,
        schedule: s.schedule === !0,
        timer: s.timer === !0
      };
    } catch {
      return t;
    }
  }
  _toggleSection(e) {
    if (this._config) {
      this._collapsed = {
        ...this._collapsed,
        [e]: !this._collapsed[e]
      };
      try {
        localStorage.setItem(
          this._storageKey(this._config.entity),
          JSON.stringify(this._collapsed)
        );
      } catch {
      }
    }
  }
  _renderCollapseButton(e, t, i) {
    const s = !this._collapsed[e];
    return l`
      <button
        class="collapse-button icon"
        title=${`${s ? "Collapse" : "Expand"} ${t.toLowerCase()}`}
        aria-label=${`${s ? "Collapse" : "Expand"} ${t.toLowerCase()}`}
        aria-expanded=${s}
        aria-controls=${i}
        @click=${() => this._toggleSection(e)}
      >
        <ha-icon icon=${s ? "mdi:chevron-up" : "mdi:chevron-down"}></ha-icon>
      </button>
    `;
  }
  async _call(e, t, i = {}) {
    if (!this.hass || !this._config || this._busy) return !1;
    this._busy = !0, this._message = "";
    try {
      return await this.hass.callService(e, t, {
        entity_id: this._config.entity,
        ...i
      }), this._message = "Saved", !0;
    } catch (s) {
      return this._message = s instanceof Error ? s.message : "Command failed", !1;
    } finally {
      this._busy = !1;
    }
  }
  _formatValue(e, t = "") {
    return typeof e == "number" ? `${e}${t}` : "--";
  }
  _modeIcon(e) {
    return {
      off: "mdi:power",
      heat: "mdi:fire",
      cool: "mdi:snowflake",
      heat_cool: "mdi:autorenew",
      auto: "mdi:calendar-sync",
      dry: "mdi:water-percent",
      fan_only: "mdi:fan"
    }[e] ?? "mdi:thermostat";
  }
  _adjustTemperature(e, t, i) {
    const s = this._state;
    if (!s) return;
    const a = s.attributes, o = {
      [e]: Math.round((t + i) * 100) / 100
    };
    e === "target_temp_low" && (o.target_temp_high = a.target_temp_high), e === "target_temp_high" && (o.target_temp_low = a.target_temp_low), this._call("climate", "set_temperature", o);
  }
  _renderTemperatureControl(e, t, i, s, a, o, n) {
    return l`
      <div class="number-control" aria-label=${e}>
        <button
          class="step-button"
          title=${`Decrease ${e.toLowerCase()}`}
          aria-label=${`Decrease ${e.toLowerCase()}`}
          ?disabled=${this._busy || i - a < o}
          @click=${() => this._adjustTemperature(t, i, -a)}
        ><ha-icon icon="mdi:minus"></ha-icon></button>
        <div class="target-value">
          <span>${i}</span><small>${s}</small>
          <label>${e}</label>
        </div>
        <button
          class="step-button"
          title=${`Increase ${e.toLowerCase()}`}
          aria-label=${`Increase ${e.toLowerCase()}`}
          ?disabled=${this._busy || i + a > n}
          @click=${() => this._adjustTemperature(t, i, a)}
        ><ha-icon icon="mdi:plus"></ha-icon></button>
      </div>
    `;
  }
  _renderSelect(e, t, i, s, a) {
    return i?.length ? l`
      <label class="field">
        <span>${e}</span>
        <select
          .value=${t ?? ""}
          ?disabled=${this._busy}
          @change=${(o) => this._call("climate", s, {
      [a]: o.target.value
    })}
        >
          ${i.map((o) => l`<option value=${o}>${o.replaceAll("_", " ")}</option>`)}
        </select>
      </label>
    ` : d;
  }
  _renderClimate(e) {
    const t = e.attributes, i = String(t.unit_of_measurement ?? "°"), s = t.hvac_modes ?? [], a = t.temperature, o = t.target_temp_low, n = t.target_temp_high, c = t.target_temp_step ?? 0.5, p = this._config?.layout === "compact";
    return l`
      <section class="climate" aria-label="Climate controls">
        ${p ? l`<div class="compact-status">
              <div>
                <span class="current-label">Current</span>
                <span class="compact-current">${this._formatValue(t.current_temperature, i)}</span>
              </div>
              ${t.hvac_action ? l`<span class="action"><span class="pulse"></span>${t.hvac_action.replaceAll("_", " ")}</span>` : d}
            </div>` : l`<div class=${`thermostat ${e.state === "off" ? "is-off" : "is-active"}`}>
              <div class="dial-ring">
                <div class="dial-content">
                  <span class="current-label">Current</span>
                  <span class="current">${this._formatValue(t.current_temperature, i)}</span>
                  ${t.hvac_action ? l`<span class="action"><span class="pulse"></span>${t.hvac_action.replaceAll("_", " ")}</span>` : d}
                </div>
              </div>
            </div>`}
        ${typeof a == "number" ? this._renderTemperatureControl(
      "Target",
      "temperature",
      a,
      i,
      c,
      t.min_temp ?? 7,
      t.max_temp ?? 35
    ) : typeof o == "number" && typeof n == "number" ? l`<div class="range-target" aria-label="Target temperature range">
                ${this._renderTemperatureControl(
      "Low",
      "target_temp_low",
      o,
      i,
      c,
      t.min_temp ?? 7,
      n
    )}
                ${this._renderTemperatureControl(
      "High",
      "target_temp_high",
      n,
      i,
      c,
      o,
      t.max_temp ?? 35
    )}
              </div>` : d}
        <div class="modes feature-buttons" role="group" aria-label="HVAC mode">
          ${s.map(
      (h) => l`
              <button
                class=${e.state === h ? "selected" : ""}
                ?disabled=${this._busy}
                aria-pressed=${e.state === h}
                @click=${() => this._call("climate", "set_hvac_mode", { hvac_mode: h })}
              ><ha-icon icon=${this._modeIcon(h)}></ha-icon><span>${h.replaceAll("_", " ")}</span></button>
            `
    )}
        </div>
        <div class="subsection-heading">
          <div><h3>Preset & options</h3><p>${t.preset_mode?.replaceAll("_", " ") ?? "Climate settings"}</p></div>
          ${this._renderCollapseButton("preset", "Preset and options", "preset-controls")}
        </div>
        <div id="preset-controls" class="control-grid" ?hidden=${this._collapsed.preset}>
              ${this._renderSelect("Preset", t.preset_mode, t.preset_modes, "set_preset_mode", "preset_mode")}
              ${this._renderSelect("Fan", t.fan_mode, t.fan_modes, "set_fan_mode", "fan_mode")}
              ${this._renderSelect("Swing", t.swing_mode, t.swing_modes, "set_swing_mode", "swing_mode")}
              ${this._renderSelect(
      "Horizontal swing",
      t.swing_horizontal_mode,
      t.swing_horizontal_modes,
      "set_swing_horizontal_mode",
      "swing_horizontal_mode"
    )}
              ${typeof t.humidity == "number" ? l`
                    <label class="field">
                      <span>Humidity</span>
                      <input
                        type="number"
                        .value=${String(t.humidity)}
                        min=${t.min_humidity ?? 30}
                        max=${t.max_humidity ?? 99}
                        ?disabled=${this._busy}
                        @change=${(h) => this._call("climate", "set_humidity", {
      humidity: Number(h.target.value)
    })}
                      />
                    </label>
                  ` : d}
          </div>
      </section>
    `;
  }
  _renderSchedule(e) {
    const t = e.attributes.next_schedule_event, i = e.attributes.schedule_id, s = e.attributes.schedule_enabled, a = i ? t ? `Next change · ${new Date(t).toLocaleString()}` : s ? "No upcoming change" : "Schedule paused" : "No schedule linked";
    return l`
      <section aria-labelledby="schedule-heading">
        <div class="section-heading">
          <ha-icon class="section-icon" icon="mdi:calendar-clock"></ha-icon>
          <div class="section-copy">
            <h3 id="schedule-heading">Schedule</h3>
            <p>${a}</p>
          </div>
          ${i ? l`<button
                class="icon"
                title=${s ? "Pause schedule" : "Resume schedule"}
                aria-label=${s ? "Pause schedule" : "Resume schedule"}
                ?disabled=${this._busy}
                @click=${() => this._call(
      "scheduled_climate",
      s ? "disable_schedule" : "enable_schedule"
    )}
              >
                <ha-icon
                  icon=${s ? "mdi:pause" : "mdi:play"}
                ></ha-icon>
              </button>` : d}
          ${this._renderCollapseButton("schedule", "Schedule", "schedule-controls")}
        </div>
        <div id="schedule-controls" class="collapsible-body" ?hidden=${this._collapsed.schedule}>
          ${i ? this._renderScheduleEditor(e) : this._renderScheduleLink(e)}
          ${this._scheduleError ? l`<p class="error" role="alert">${this._scheduleError}</p>` : d}
        </div>
      </section>
    `;
  }
  _renderScheduleLink(e) {
    const t = e.attributes.legacy_schedule;
    return this._canEditSchedule ? l`
      <p class="caption">
        ${t ? `Your old daily times (${m(t.on_time)} – ${m(t.off_time)}) can be converted into a weekly schedule.` : "Create a schedule helper to control this entity on a weekly plan."}
      </p>
      <div class="timer-actions">
        <button class="primary" ?disabled=${this._busy} @click=${() => this._createSchedule()}>
          <ha-icon icon="mdi:calendar-plus"></ha-icon>Create schedule
        </button>
      </div>
    ` : l`<p class="caption">Link a schedule helper from the integration options to control this entity on a weekly plan.</p>`;
  }
  _renderScheduleEditor(e) {
    if (!this._schedule)
      return l`<p class="caption">Loading the linked schedule…</p>`;
    const t = R(this._schedule[this._selectedDay] ?? []);
    return l`
      <div class="day-chips" role="tablist" aria-label="Days of the week">
        ${S.map(
      (i) => l`
            <button
              role="tab"
              aria-selected=${i === this._selectedDay}
              class=${i === this._selectedDay ? "selected" : ""}
              @click=${() => this._selectDay(i)}
            >
              ${O[i]}
            </button>
          `
    )}
      </div>
      <ul class="block-list">
        ${t.length === 0 ? l`<li class="caption">No blocks on ${O[this._selectedDay]}</li>` : t.map(
      (i, s) => l`
                <li class="block">
                  <div class="block-copy">
                    <span>${m(i.from)} – ${m(i.to)}</span>
                    <small>${Ke(i)}</small>
                  </div>
                  ${this._canEditSchedule ? l`
                        <button class="icon" title="Edit block" aria-label="Edit block" @click=${() => this._draft = me(i, s)}>
                          <ha-icon icon="mdi:pencil-outline"></ha-icon>
                        </button>
                        <button class="icon" title="Duplicate block" aria-label="Duplicate block" @click=${() => this._duplicateBlock(s)}>
                          <ha-icon icon="mdi:content-duplicate"></ha-icon>
                        </button>
                        <button class="icon" title="Delete block" aria-label="Delete block" @click=${() => this._deleteBlock(s)}>
                          <ha-icon icon="mdi:delete-outline"></ha-icon>
                        </button>
                      ` : d}
                </li>
              `
    )}
      </ul>
      ${this._canEditSchedule ? l`
            <div class="timer-actions">
              <button class="primary" ?disabled=${this._busy} @click=${() => this._draft = We()}>
                <ha-icon icon="mdi:plus"></ha-icon>Add block
              </button>
              <label class="custom-time">
                <span>Copy to</span>
                <select
                  ?disabled=${this._busy}
                  .value=${""}
                  @change=${(i) => this._copyDay(i.target)}
                >
                  <option value="">Select a day</option>
                  ${S.filter((i) => i !== this._selectedDay).map(
      (i) => l`<option value=${i}>${O[i]}</option>`
    )}
                </select>
              </label>
            </div>
            ${this._draft ? this._renderDraft(e, this._draft) : d}
          ` : l`<p class="caption">Only administrators can change this schedule.</p>`}
    `;
  }
  _renderDraft(e, t) {
    const i = e.attributes, s = i.supported_features ?? 0, a = (n) => {
      this._draft = { ...this._draft ?? t, ...n };
    }, o = (n) => n.target.value;
    return l`
      <div class="schedule-grid">
        <label class="field"><span>From</span><input type="time" .value=${t.from} @input=${(n) => a({ from: o(n) })} /></label>
        <label class="field"><span>To</span><input type="time" .value=${t.to} @input=${(n) => a({ to: o(n) })} /></label>
        <label class="field">
          <span>Mode</span>
          <select .value=${t.hvac_mode} @change=${(n) => a({ hvac_mode: o(n) })}>
            <option value="">Unchanged</option>
            ${(i.hvac_modes ?? []).map(
      (n) => l`<option value=${n} ?selected=${n === t.hvac_mode}>${n.replaceAll("_", " ")}</option>`
    )}
          </select>
        </label>
        ${s & 8 && (i.fan_modes ?? []).length > 0 ? l`
              <label class="field">
                <span>Fan</span>
                <select .value=${t.fan_mode} @change=${(n) => a({ fan_mode: o(n) })}>
                  <option value="">Unchanged</option>
                  ${(i.fan_modes ?? []).map(
      (n) => l`<option value=${n} ?selected=${n === t.fan_mode}>${n}</option>`
    )}
                </select>
              </label>
            ` : d}
        ${s & 1 ? l`<label class="field"><span>Temperature</span><input type="number" min=${i.min_temp ?? 7} max=${i.max_temp ?? 35} step=${i.target_temp_step ?? 0.5} .value=${t.temperature} @input=${(n) => a({ temperature: o(n) })} /></label>` : d}
        ${s & 2 ? l`
              <label class="field"><span>Low</span><input type="number" min=${i.min_temp ?? 7} max=${i.max_temp ?? 35} step=${i.target_temp_step ?? 0.5} .value=${t.target_temp_low} @input=${(n) => a({ target_temp_low: o(n) })} /></label>
              <label class="field"><span>High</span><input type="number" min=${i.min_temp ?? 7} max=${i.max_temp ?? 35} step=${i.target_temp_step ?? 0.5} .value=${t.target_temp_high} @input=${(n) => a({ target_temp_high: o(n) })} /></label>
            ` : d}
        ${s & 4 ? l`<label class="field"><span>Humidity</span><input type="number" min=${i.min_humidity ?? 30} max=${i.max_humidity ?? 99} step="1" .value=${t.humidity} @input=${(n) => a({ humidity: o(n) })} /></label>` : d}
        <div class="timer-actions">
          <button class="primary" ?disabled=${this._busy} @click=${() => this._saveDraft()}><ha-icon icon="mdi:content-save-outline"></ha-icon>Save block</button>
          <button ?disabled=${this._busy} @click=${() => this._draft = void 0}>Cancel</button>
        </div>
      </div>
    `;
  }
  _selectDay(e) {
    this._selectedDay = e, this._draft = void 0, this._scheduleError = "";
  }
  _dayBlocks() {
    return R(this._schedule?.[this._selectedDay] ?? []);
  }
  async _saveDraft() {
    const e = this._draft;
    if (!this._schedule || !e) return;
    const t = this._dayBlocks(), i = Fe(e, t);
    if (i) {
      this._scheduleError = i;
      return;
    }
    const s = [...t];
    e.index === null ? s.push(pe(e)) : s[e.index] = pe(e), await this._writeSchedule(F(this._schedule, this._selectedDay, s)) && (this._draft = void 0);
  }
  async _duplicateBlock(e) {
    if (!this._schedule) return;
    const i = this._dayBlocks()[e];
    i && (this._draft = { ...me(i, e), index: null }, this._scheduleError = "");
  }
  async _deleteBlock(e) {
    if (!this._schedule) return;
    const t = this._dayBlocks().filter((i, s) => s !== e);
    this._draft = void 0, await this._writeSchedule(F(this._schedule, this._selectedDay, t));
  }
  async _copyDay(e) {
    const t = e.value;
    e.value = "", !(!this._schedule || !t) && await this._writeSchedule(
      F(this._schedule, t, this._dayBlocks())
    );
  }
  async _writeSchedule(e) {
    if (!this.hass || this._busy) return !1;
    this._busy = !0, this._scheduleError = "", this._message = "";
    try {
      return await this.hass.callWS(qe(e)), this._schedule = e, this._message = "Saved", !0;
    } catch (t) {
      return this._scheduleError = t instanceof Error ? t.message : "Unable to save the schedule", !1;
    } finally {
      this._busy = !1;
    }
  }
  async _createSchedule() {
    const e = this._state;
    if (!this.hass || !e || this._busy) return;
    const t = Je(e.attributes.legacy_schedule), i = {
      type: "schedule/create",
      name: this._config?.name ?? e.attributes.friendly_name ?? "Scheduled Climate"
    };
    for (const a of S) i[a] = t;
    this._busy = !0, this._scheduleError = "";
    let s;
    try {
      s = await this.hass.callWS(i);
    } catch (a) {
      this._scheduleError = a instanceof Error ? a.message : "Unable to create the schedule";
    } finally {
      this._busy = !1;
    }
    s && await this._call("scheduled_climate", "link_schedule", {
      schedule_id: s.id
    });
  }
  _renderTimer(e) {
    const t = e.attributes.timer_action, i = e.attributes.timer_deadline, s = this._config?.timer_presets ?? D;
    return l`
      <section aria-labelledby="timer-heading">
        <div class="section-heading">
          <ha-icon class="section-icon" icon="mdi:timer-outline"></ha-icon>
          <div class="section-copy"><h3 id="timer-heading">Timer</h3><p>${t && i ? `${t} at ${new Date(i).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : "No active timer"}</p></div>
          ${t ? l`<button class="icon" title="Cancel timer" aria-label="Cancel timer" @click=${() => this._call("scheduled_climate", "cancel_timer")}><ha-icon icon="mdi:timer-off-outline"></ha-icon></button>` : d}
          ${this._renderCollapseButton("timer", "Timer", "timer-controls")}
        </div>
        <div id="timer-controls" class="collapsible-body" ?hidden=${this._collapsed.timer}>
        <div class="presets" aria-label="Timer presets">
          ${s.map((a) => l`<button class=${this._timerMinutes === a ? "selected" : ""} @click=${() => this._timerMinutes = a}>${a < 60 ? `${a}m` : `${a / 60}h`}</button>`)}
          <label class="custom-time"><span>Minutes</span><input type="number" min="1" step="1" .value=${String(this._timerMinutes)} @input=${(a) => this._timerMinutes = Math.max(1, Number(a.target.value))} /></label>
        </div>
        <div class="timer-actions">
          <button class="primary" ?disabled=${this._busy} @click=${() => this._startTimer("on")}><ha-icon icon="mdi:power"></ha-icon>Turn on later</button>
          <button ?disabled=${this._busy} @click=${() => this._startTimer("off")}><ha-icon icon="mdi:power-off"></ha-icon>Turn off later</button>
        </div>
        </div>
      </section>
    `;
  }
  _startTimer(e) {
    const t = Math.round(this._timerMinutes * 60);
    this._call("scheduled_climate", `start_${e}_timer`, {
      duration: { seconds: t }
    });
  }
  render() {
    if (!this._config || !this.hass) return d;
    const e = this._state;
    if (!e) return l`<ha-card><div class="empty">Entity not found</div></ha-card>`;
    const t = Ye.has(e.state), i = this._config.name ?? e.attributes.friendly_name ?? "Scheduled Climate";
    return l`
      <ha-card class=${`state-${e.state} ${this._config.layout === "compact" ? "compact" : "standard"}`}>
        <header>
          <div class="title-block"><h2>${i}</h2><p>${t ? "Unavailable" : e.state.replaceAll("_", " ")}</p></div>
          <button class="more-info icon" title="More information" aria-label="More information" @click=${this._showMoreInfo}>
            <ha-icon icon="mdi:dots-vertical"></ha-icon>
          </button>
        </header>
        ${t ? l`<div class="empty">The climate entity is unavailable.</div>` : this._renderClimate(e)}
        ${!t && this._config.show_schedule !== !1 ? this._renderSchedule(e) : d}
        ${!t && this._config.show_timer !== !1 ? this._renderTimer(e) : d}
        ${this._message ? l`<div class="message" role="status">${this._message}</div>` : d}
      </ha-card>
    `;
  }
  _showMoreInfo() {
    this._config && this.dispatchEvent(new CustomEvent("hass-more-info", {
      bubbles: !0,
      composed: !0,
      detail: { entityId: this._config.entity }
    }));
  }
};
I.properties = {
  hass: { attribute: !1 },
  _config: { state: !0 },
  _busy: { state: !0 },
  _message: { state: !0 },
  _timerMinutes: { state: !0 },
  _collapsed: { state: !0 },
  _schedule: { state: !0 },
  _selectedDay: { state: !0 },
  _draft: { state: !0 },
  _scheduleError: { state: !0 }
}, I.styles = ge`
    :host { display: block; color: var(--primary-text-color); --feature-color: var(--state-climate-heat-color, var(--primary-color)); }
    ha-card { overflow: hidden; border-radius: var(--ha-card-border-radius, var(--ha-border-radius-lg, 12px)); }
    ha-card.state-cool { --feature-color: var(--state-climate-cool-color, #2196f3); }
    ha-card.state-dry { --feature-color: var(--state-climate-dry-color, #f9a825); }
    ha-card.state-fan_only { --feature-color: var(--state-climate-fan_only-color, #8e8e93); }
    ha-card.state-off { --feature-color: var(--state-climate-off-color, var(--state-inactive-color, #9e9e9e)); }
    header, section { padding: 16px 20px; }
    header { position: relative; min-height: 50px; display: flex; justify-content: center; align-items: center; box-sizing: border-box; }
    .title-block { min-width: 0; text-align: center; }
    .title-block p { text-transform: capitalize; }
    .more-info { position: absolute; right: 8px; inset-inline-end: 8px; border: 0; border-radius: var(--ha-border-radius-pill, 999px); color: var(--secondary-text-color); background: transparent; }
    h2, h3, p { margin: 0; letter-spacing: 0; }
    h2 { overflow: hidden; font-size: var(--ha-font-size-l, 18px); line-height: var(--ha-line-height-expanded, 1.4); text-overflow: ellipsis; white-space: nowrap; }
    h3 { font-size: var(--ha-font-size-m, 14px); line-height: 1.4; }
    p, .caption, .field > span, .custom-time > span { color: var(--secondary-text-color); font-size: 12px; }
    section + section { border-top: 1px solid var(--divider-color); }
    .climate { padding-top: 4px; }
    .thermostat { display: grid; place-items: center; padding: 8px 0 14px; }
    .dial-ring { width: min(230px, 68vw); aspect-ratio: 1; display: grid; place-items: center; border: 12px solid color-mix(in srgb, var(--feature-color) 72%, var(--card-background-color)); border-right-color: color-mix(in srgb, var(--feature-color) 16%, var(--card-background-color)); border-radius: 50%; box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--feature-color) 18%, transparent); box-sizing: border-box; }
    .is-off .dial-ring { border-color: color-mix(in srgb, var(--secondary-text-color) 22%, var(--card-background-color)); }
    .dial-content { display: grid; justify-items: center; gap: 3px; }
    .current-label { color: var(--secondary-text-color); font-size: 12px; }
    .current { font-size: 48px; line-height: 1.05; font-weight: 400; font-variant-numeric: tabular-nums; }
    .compact-status { display: flex; min-height: 52px; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 10px; }
    .compact-status > div { display: grid; }
    .compact-current { font-size: 30px; line-height: 1.1; font-weight: 400; font-variant-numeric: tabular-nums; }
    .action { display: flex; align-items: center; gap: 6px; color: var(--secondary-text-color); font-size: 12px; text-transform: capitalize; }
    .pulse { width: 7px; height: 7px; border-radius: 50%; background: var(--state-climate-heat-color, var(--primary-color)); }
    .number-control { display: grid; grid-template-columns: 44px minmax(80px, 1fr) 44px; align-items: center; max-width: 260px; margin: 0 auto; border: 1px solid var(--divider-color); border-radius: var(--ha-border-radius-pill, 999px); overflow: hidden; }
    .target-value { display: grid; grid-template-columns: auto auto; justify-content: center; align-items: start; padding: 5px 8px; text-align: center; }
    .target-value span { font-size: 22px; font-variant-numeric: tabular-nums; }
    .target-value small { padding-top: 2px; font-size: 12px; }
    .target-value label { grid-column: 1 / -1; color: var(--secondary-text-color); font-size: 10px; }
    .range-target { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .range-target .number-control { grid-template-columns: 36px minmax(56px, 1fr) 36px; width: 100%; }
    .modes, .presets { display: flex; gap: 8px; overflow-x: auto; margin-top: 16px; padding-bottom: 2px; scrollbar-width: thin; }
    button { min-height: 40px; padding: 8px 12px; border: 1px solid var(--divider-color); border-radius: var(--ha-border-radius-pill, 999px); color: var(--primary-text-color); background: var(--card-background-color); font: inherit; cursor: pointer; text-transform: capitalize; white-space: nowrap; }
    button:hover { background: color-mix(in srgb, var(--primary-color) 8%, var(--card-background-color)); }
    button:focus-visible, input:focus-visible, select:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
    button.selected, button.primary { color: var(--text-primary-color, white); background: var(--feature-color); border-color: var(--feature-color); }
    button:disabled { opacity: .55; cursor: wait; }
    button ha-icon { --mdc-icon-size: 18px; margin-right: 6px; vertical-align: -4px; }
    .step-button { min-height: 44px; padding: 8px; border: 0; border-radius: 0; color: var(--feature-color); background: transparent; }
    .step-button ha-icon, .icon ha-icon { margin: 0; }
    .feature-buttons button { display: grid; min-width: 64px; justify-items: center; gap: 3px; padding: 7px 12px; font-size: 11px; }
    .feature-buttons button ha-icon { --mdc-icon-size: 20px; margin: 0; }
    .control-grid, .schedule-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 16px; padding: 12px; border-radius: var(--ha-border-radius-lg, 12px); background: var(--secondary-background-color, color-mix(in srgb, var(--primary-text-color) 5%, var(--card-background-color))); }
    .field { display: grid; gap: 5px; }
    .day-chips { display: flex; gap: 6px; overflow-x: auto; margin-top: 12px; padding-bottom: 2px; scrollbar-width: thin; }
    .day-chips button { flex: 1 0 auto; min-width: 48px; padding: 8px 10px; }
    .block-list { display: grid; gap: 8px; margin: 12px 0 0; padding: 0; list-style: none; }
    .block { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border: 1px solid var(--divider-color); border-radius: var(--ha-border-radius-lg, 12px); }
    .block-copy { display: grid; flex: 1 1 auto; min-width: 0; gap: 2px; }
    .block-copy span { font-variant-numeric: tabular-nums; }
    .block-copy small { color: var(--secondary-text-color); font-size: 12px; text-transform: capitalize; }
    .block .icon { min-height: 36px; padding: 6px; }
    .error { margin-top: 12px; color: var(--error-color, #db4437); font-size: 12px; }
    input, select { box-sizing: border-box; min-width: 0; min-height: 40px; padding: 7px 10px; color: var(--primary-text-color); background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: var(--ha-border-radius-md, 8px); font: inherit; }
    input[type="checkbox"] { accent-color: var(--primary-color); }
    .section-heading { display: flex; align-items: center; gap: 12px; }
    .subsection-heading { display: flex; align-items: center; gap: 12px; margin-top: 16px; }
    .subsection-heading > div { min-width: 0; flex: 1; }
    .subsection-heading p { margin-top: 3px; text-transform: capitalize; }
    .section-icon { --mdc-icon-size: 22px; flex: 0 0 auto; padding: 9px; border-radius: 50%; color: var(--feature-color); background: color-mix(in srgb, var(--feature-color) 12%, var(--card-background-color)); }
    .section-copy { min-width: 0; flex: 1; }
    .section-heading p { margin-top: 3px; }
    .switch { display: flex; align-items: center; gap: 7px; font-size: 13px; }
    .schedule-grid .primary { align-self: end; }
    .icon { width: 40px; padding: 7px; }
    .icon ha-icon { margin: 0; }
    .collapse-button { flex: 0 0 auto; border: 0; color: var(--secondary-text-color); background: transparent; }
    [hidden] { display: none !important; }
    .custom-time { display: flex; align-items: center; gap: 6px; margin-left: auto; }
    .custom-time input { width: 68px; }
    .timer-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 14px; }
    .message { padding: 10px 20px; border-top: 1px solid var(--divider-color); color: var(--secondary-text-color); font-size: 13px; }
    .empty { padding: 28px 20px; color: var(--secondary-text-color); text-align: center; }
    ha-card.compact header { min-height: 44px; padding-block: 10px; }
    ha-card.compact .climate { padding: 4px 16px 12px; }
    ha-card.compact .modes { margin-top: 12px; }
    ha-card.compact .subsection-heading { margin-top: 12px; }
    ha-card.compact section:not(.climate) { padding: 12px 16px; }
    ha-card.compact .control-grid, ha-card.compact .schedule-grid { margin-top: 10px; }
    ha-card.compact .feature-buttons button { min-height: 44px; }
    @media (max-width: 420px) {
      header, section { padding: 16px; }
      .control-grid, .schedule-grid { grid-template-columns: 1fr; }
      .timer-actions { grid-template-columns: 1fr; }
      .current { font-size: 42px; }
      .custom-time { margin-left: 0; }
      .range-target { grid-template-columns: 1fr; }
      ha-card.compact .range-target { grid-template-columns: 1fr 1fr; }
      .presets { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); overflow-x: visible; }
      .presets > button { min-width: 0; padding-inline: 6px; }
      .custom-time { grid-column: 1 / -1; width: 100%; }
      .custom-time input { flex: 1; width: auto; }
    }
  `;
let Y = I;
customElements.get("scheduled-climate-card") || customElements.define("scheduled-climate-card", Y);
window.customCards = window.customCards ?? [];
window.customCards.some((r) => r.type === "scheduled-climate-card") || window.customCards.push({
  type: "scheduled-climate-card",
  name: "Scheduled Climate Card",
  description: "Climate controls with daily schedules and one-shot timers.",
  preview: !0
});
export {
  Y as ScheduledClimateCard
};
