const R = globalThis, it = R.ShadowRoot && (R.ShadyCSS === void 0 || R.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, at = /* @__PURE__ */ Symbol(), ct = /* @__PURE__ */ new WeakMap();
let Et = class {
  constructor(t, e, s) {
    if (this._$cssResult$ = !0, s !== at) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = t, this.t = e;
  }
  get styleSheet() {
    let t = this.o;
    const e = this.t;
    if (it && t === void 0) {
      const s = e !== void 0 && e.length === 1;
      s && (t = ct.get(e)), t === void 0 && ((this.o = t = new CSSStyleSheet()).replaceSync(this.cssText), s && ct.set(e, t));
    }
    return t;
  }
  toString() {
    return this.cssText;
  }
};
const zt = (r) => new Et(typeof r == "string" ? r : r + "", void 0, at), P = (r, ...t) => {
  const e = r.length === 1 ? r[0] : t.reduce((s, i, a) => s + ((n) => {
    if (n._$cssResult$ === !0) return n.cssText;
    if (typeof n == "number") return n;
    throw Error("Value passed to 'css' function must be a 'css' function result: " + n + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
  })(i) + r[a + 1], r[0]);
  return new Et(e, r, at);
}, Ut = (r, t) => {
  if (it) r.adoptedStyleSheets = t.map((e) => e instanceof CSSStyleSheet ? e : e.styleSheet);
  else for (const e of t) {
    const s = document.createElement("style"), i = R.litNonce;
    i !== void 0 && s.setAttribute("nonce", i), s.textContent = e.cssText, r.appendChild(s);
  }
}, dt = it ? (r) => r : (r) => r instanceof CSSStyleSheet ? ((t) => {
  let e = "";
  for (const s of t.cssRules) e += s.cssText;
  return zt(e);
})(r) : r;
const { is: It, defineProperty: Ht, getOwnPropertyDescriptor: Nt, getOwnPropertyNames: Rt, getOwnPropertySymbols: Bt, getPrototypeOf: Lt } = Object, q = globalThis, ht = q.trustedTypes, jt = ht ? ht.emptyScript : "", Vt = q.reactiveElementPolyfillSupport, M = (r, t) => r, G = { toAttribute(r, t) {
  switch (t) {
    case Boolean:
      r = r ? jt : null;
      break;
    case Object:
    case Array:
      r = r == null ? r : JSON.stringify(r);
  }
  return r;
}, fromAttribute(r, t) {
  let e = r;
  switch (t) {
    case Boolean:
      e = r !== null;
      break;
    case Number:
      e = r === null ? null : Number(r);
      break;
    case Object:
    case Array:
      try {
        e = JSON.parse(r);
      } catch {
        e = null;
      }
  }
  return e;
} }, Tt = (r, t) => !It(r, t), pt = { attribute: !0, type: String, converter: G, reflect: !1, useDefault: !1, hasChanged: Tt };
Symbol.metadata ??= /* @__PURE__ */ Symbol("metadata"), q.litPropertyMetadata ??= /* @__PURE__ */ new WeakMap();
let E = class extends HTMLElement {
  static addInitializer(t) {
    this._$Ei(), (this.l ??= []).push(t);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(t, e = pt) {
    if (e.state && (e.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(t) && ((e = Object.create(e)).wrapped = !0), this.elementProperties.set(t, e), !e.noAccessor) {
      const s = /* @__PURE__ */ Symbol(), i = this.getPropertyDescriptor(t, s, e);
      i !== void 0 && Ht(this.prototype, t, i);
    }
  }
  static getPropertyDescriptor(t, e, s) {
    const { get: i, set: a } = Nt(this.prototype, t) ?? { get() {
      return this[e];
    }, set(n) {
      this[e] = n;
    } };
    return { get: i, set(n) {
      const o = i?.call(this);
      a?.call(this, n), this.requestUpdate(t, o, s);
    }, configurable: !0, enumerable: !0 };
  }
  static getPropertyOptions(t) {
    return this.elementProperties.get(t) ?? pt;
  }
  static _$Ei() {
    if (this.hasOwnProperty(M("elementProperties"))) return;
    const t = Lt(this);
    t.finalize(), t.l !== void 0 && (this.l = [...t.l]), this.elementProperties = new Map(t.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(M("finalized"))) return;
    if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(M("properties"))) {
      const e = this.properties, s = [...Rt(e), ...Bt(e)];
      for (const i of s) this.createProperty(i, e[i]);
    }
    const t = this[Symbol.metadata];
    if (t !== null) {
      const e = litPropertyMetadata.get(t);
      if (e !== void 0) for (const [s, i] of e) this.elementProperties.set(s, i);
    }
    this._$Eh = /* @__PURE__ */ new Map();
    for (const [e, s] of this.elementProperties) {
      const i = this._$Eu(e, s);
      i !== void 0 && this._$Eh.set(i, e);
    }
    this.elementStyles = this.finalizeStyles(this.styles);
  }
  static finalizeStyles(t) {
    const e = [];
    if (Array.isArray(t)) {
      const s = new Set(t.flat(1 / 0).reverse());
      for (const i of s) e.unshift(dt(i));
    } else t !== void 0 && e.push(dt(t));
    return e;
  }
  static _$Eu(t, e) {
    const s = e.attribute;
    return s === !1 ? void 0 : typeof s == "string" ? s : typeof t == "string" ? t.toLowerCase() : void 0;
  }
  constructor() {
    super(), this._$Ep = void 0, this.isUpdatePending = !1, this.hasUpdated = !1, this._$Em = null, this._$Ev();
  }
  _$Ev() {
    this._$ES = new Promise((t) => this.enableUpdating = t), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), this.constructor.l?.forEach((t) => t(this));
  }
  addController(t) {
    (this._$EO ??= /* @__PURE__ */ new Set()).add(t), this.renderRoot !== void 0 && this.isConnected && t.hostConnected?.();
  }
  removeController(t) {
    this._$EO?.delete(t);
  }
  _$E_() {
    const t = /* @__PURE__ */ new Map(), e = this.constructor.elementProperties;
    for (const s of e.keys()) this.hasOwnProperty(s) && (t.set(s, this[s]), delete this[s]);
    t.size > 0 && (this._$Ep = t);
  }
  createRenderRoot() {
    const t = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
    return Ut(t, this.constructor.elementStyles), t;
  }
  connectedCallback() {
    this.renderRoot ??= this.createRenderRoot(), this.enableUpdating(!0), this._$EO?.forEach((t) => t.hostConnected?.());
  }
  enableUpdating(t) {
  }
  disconnectedCallback() {
    this._$EO?.forEach((t) => t.hostDisconnected?.());
  }
  attributeChangedCallback(t, e, s) {
    this._$AK(t, s);
  }
  _$ET(t, e) {
    const s = this.constructor.elementProperties.get(t), i = this.constructor._$Eu(t, s);
    if (i !== void 0 && s.reflect === !0) {
      const a = (s.converter?.toAttribute !== void 0 ? s.converter : G).toAttribute(e, s.type);
      this._$Em = t, a == null ? this.removeAttribute(i) : this.setAttribute(i, a), this._$Em = null;
    }
  }
  _$AK(t, e) {
    const s = this.constructor, i = s._$Eh.get(t);
    if (i !== void 0 && this._$Em !== i) {
      const a = s.getPropertyOptions(i), n = typeof a.converter == "function" ? { fromAttribute: a.converter } : a.converter?.fromAttribute !== void 0 ? a.converter : G;
      this._$Em = i;
      const o = n.fromAttribute(e, a.type);
      this[i] = o ?? this._$Ej?.get(i) ?? o, this._$Em = null;
    }
  }
  requestUpdate(t, e, s, i = !1, a) {
    if (t !== void 0) {
      const n = this.constructor;
      if (i === !1 && (a = this[t]), s ??= n.getPropertyOptions(t), !((s.hasChanged ?? Tt)(a, e) || s.useDefault && s.reflect && a === this._$Ej?.get(t) && !this.hasAttribute(n._$Eu(t, s)))) return;
      this.C(t, e, s);
    }
    this.isUpdatePending === !1 && (this._$ES = this._$EP());
  }
  C(t, e, { useDefault: s, reflect: i, wrapped: a }, n) {
    s && !(this._$Ej ??= /* @__PURE__ */ new Map()).has(t) && (this._$Ej.set(t, n ?? e ?? this[t]), a !== !0 || n !== void 0) || (this._$AL.has(t) || (this.hasUpdated || s || (e = void 0), this._$AL.set(t, e)), i === !0 && this._$Em !== t && (this._$Eq ??= /* @__PURE__ */ new Set()).add(t));
  }
  async _$EP() {
    this.isUpdatePending = !0;
    try {
      await this._$ES;
    } catch (e) {
      Promise.reject(e);
    }
    const t = this.scheduleUpdate();
    return t != null && await t, !this.isUpdatePending;
  }
  scheduleUpdate() {
    return this.performUpdate();
  }
  performUpdate() {
    if (!this.isUpdatePending) return;
    if (!this.hasUpdated) {
      if (this.renderRoot ??= this.createRenderRoot(), this._$Ep) {
        for (const [i, a] of this._$Ep) this[i] = a;
        this._$Ep = void 0;
      }
      const s = this.constructor.elementProperties;
      if (s.size > 0) for (const [i, a] of s) {
        const { wrapped: n } = a, o = this[i];
        n !== !0 || this._$AL.has(i) || o === void 0 || this.C(i, void 0, a, o);
      }
    }
    let t = !1;
    const e = this._$AL;
    try {
      t = this.shouldUpdate(e), t ? (this.willUpdate(e), this._$EO?.forEach((s) => s.hostUpdate?.()), this.update(e)) : this._$EM();
    } catch (s) {
      throw t = !1, this._$EM(), s;
    }
    t && this._$AE(e);
  }
  willUpdate(t) {
  }
  _$AE(t) {
    this._$EO?.forEach((e) => e.hostUpdated?.()), this.hasUpdated || (this.hasUpdated = !0, this.firstUpdated(t)), this.updated(t);
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
  shouldUpdate(t) {
    return !0;
  }
  update(t) {
    this._$Eq &&= this._$Eq.forEach((e) => this._$ET(e, this[e])), this._$EM();
  }
  updated(t) {
  }
  firstUpdated(t) {
  }
};
E.elementStyles = [], E.shadowRootOptions = { mode: "open" }, E[M("elementProperties")] = /* @__PURE__ */ new Map(), E[M("finalized")] = /* @__PURE__ */ new Map(), Vt?.({ ReactiveElement: E }), (q.reactiveElementVersions ??= []).push("2.1.2");
const rt = globalThis, ut = (r) => r, L = rt.trustedTypes, mt = L ? L.createPolicy("lit-html", { createHTML: (r) => r }) : void 0, Ct = "$lit$", v = `lit$${Math.random().toFixed(9).slice(2)}$`, Pt = "?" + v, Wt = `<${Pt}>`, S = document, z = () => S.createComment(""), U = (r) => r === null || typeof r != "object" && typeof r != "function", ot = Array.isArray, Kt = (r) => ot(r) || typeof r?.[Symbol.iterator] == "function", J = `[ 	
\f\r]`, O = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, _t = /-->/g, gt = />/g, x = RegExp(`>|${J}(?:([^\\s"'>=/]+)(${J}*=${J}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g"), ft = /'/g, bt = /"/g, Ot = /^(?:script|style|textarea|title)$/i, Ft = (r) => (t, ...e) => ({ _$litType$: r, strings: t, values: e }), l = Ft(1), T = /* @__PURE__ */ Symbol.for("lit-noChange"), c = /* @__PURE__ */ Symbol.for("lit-nothing"), $t = /* @__PURE__ */ new WeakMap(), w = S.createTreeWalker(S, 129);
function Mt(r, t) {
  if (!ot(r) || !r.hasOwnProperty("raw")) throw Error("invalid template strings array");
  return mt !== void 0 ? mt.createHTML(t) : t;
}
const qt = (r, t) => {
  const e = r.length - 1, s = [];
  let i, a = t === 2 ? "<svg>" : t === 3 ? "<math>" : "", n = O;
  for (let o = 0; o < e; o++) {
    const d = r[o];
    let u, h, p = -1, _ = 0;
    for (; _ < d.length && (n.lastIndex = _, h = n.exec(d), h !== null); ) _ = n.lastIndex, n === O ? h[1] === "!--" ? n = _t : h[1] !== void 0 ? n = gt : h[2] !== void 0 ? (Ot.test(h[2]) && (i = RegExp("</" + h[2], "g")), n = x) : h[3] !== void 0 && (n = x) : n === x ? h[0] === ">" ? (n = i ?? O, p = -1) : h[1] === void 0 ? p = -2 : (p = n.lastIndex - h[2].length, u = h[1], n = h[3] === void 0 ? x : h[3] === '"' ? bt : ft) : n === bt || n === ft ? n = x : n === _t || n === gt ? n = O : (n = x, i = void 0);
    const y = n === x && r[o + 1].startsWith("/>") ? " " : "";
    a += n === O ? d + Wt : p >= 0 ? (s.push(u), d.slice(0, p) + Ct + d.slice(p) + v + y) : d + v + (p === -2 ? o : y);
  }
  return [Mt(r, a + (r[e] || "<?>") + (t === 2 ? "</svg>" : t === 3 ? "</math>" : "")), s];
};
class I {
  constructor({ strings: t, _$litType$: e }, s) {
    let i;
    this.parts = [];
    let a = 0, n = 0;
    const o = t.length - 1, d = this.parts, [u, h] = qt(t, e);
    if (this.el = I.createElement(u, s), w.currentNode = this.el.content, e === 2 || e === 3) {
      const p = this.el.content.firstChild;
      p.replaceWith(...p.childNodes);
    }
    for (; (i = w.nextNode()) !== null && d.length < o; ) {
      if (i.nodeType === 1) {
        if (i.hasAttributes()) for (const p of i.getAttributeNames()) if (p.endsWith(Ct)) {
          const _ = h[n++], y = i.getAttribute(p).split(v), N = /([.?@])?(.*)/.exec(_);
          d.push({ type: 1, index: a, name: N[2], strings: y, ctor: N[1] === "." ? Jt : N[1] === "?" ? Zt : N[1] === "@" ? Gt : Y }), i.removeAttribute(p);
        } else p.startsWith(v) && (d.push({ type: 6, index: a }), i.removeAttribute(p));
        if (Ot.test(i.tagName)) {
          const p = i.textContent.split(v), _ = p.length - 1;
          if (_ > 0) {
            i.textContent = L ? L.emptyScript : "";
            for (let y = 0; y < _; y++) i.append(p[y], z()), w.nextNode(), d.push({ type: 2, index: ++a });
            i.append(p[_], z());
          }
        }
      } else if (i.nodeType === 8) if (i.data === Pt) d.push({ type: 2, index: a });
      else {
        let p = -1;
        for (; (p = i.data.indexOf(v, p + 1)) !== -1; ) d.push({ type: 7, index: a }), p += v.length - 1;
      }
      a++;
    }
  }
  static createElement(t, e) {
    const s = S.createElement("template");
    return s.innerHTML = t, s;
  }
}
function C(r, t, e = r, s) {
  if (t === T) return t;
  let i = s !== void 0 ? e._$Co?.[s] : e._$Cl;
  const a = U(t) ? void 0 : t._$litDirective$;
  return i?.constructor !== a && (i?._$AO?.(!1), a === void 0 ? i = void 0 : (i = new a(r), i._$AT(r, e, s)), s !== void 0 ? (e._$Co ??= [])[s] = i : e._$Cl = i), i !== void 0 && (t = C(r, i._$AS(r, t.values), i, s)), t;
}
class Yt {
  constructor(t, e) {
    this._$AV = [], this._$AN = void 0, this._$AD = t, this._$AM = e;
  }
  get parentNode() {
    return this._$AM.parentNode;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  u(t) {
    const { el: { content: e }, parts: s } = this._$AD, i = (t?.creationScope ?? S).importNode(e, !0);
    w.currentNode = i;
    let a = w.nextNode(), n = 0, o = 0, d = s[0];
    for (; d !== void 0; ) {
      if (n === d.index) {
        let u;
        d.type === 2 ? u = new H(a, a.nextSibling, this, t) : d.type === 1 ? u = new d.ctor(a, d.name, d.strings, this, t) : d.type === 6 && (u = new Xt(a, this, t)), this._$AV.push(u), d = s[++o];
      }
      n !== d?.index && (a = w.nextNode(), n++);
    }
    return w.currentNode = S, i;
  }
  p(t) {
    let e = 0;
    for (const s of this._$AV) s !== void 0 && (s.strings !== void 0 ? (s._$AI(t, s, e), e += s.strings.length - 2) : s._$AI(t[e])), e++;
  }
}
class H {
  get _$AU() {
    return this._$AM?._$AU ?? this._$Cv;
  }
  constructor(t, e, s, i) {
    this.type = 2, this._$AH = c, this._$AN = void 0, this._$AA = t, this._$AB = e, this._$AM = s, this.options = i, this._$Cv = i?.isConnected ?? !0;
  }
  get parentNode() {
    let t = this._$AA.parentNode;
    const e = this._$AM;
    return e !== void 0 && t?.nodeType === 11 && (t = e.parentNode), t;
  }
  get startNode() {
    return this._$AA;
  }
  get endNode() {
    return this._$AB;
  }
  _$AI(t, e = this) {
    t = C(this, t, e), U(t) ? t === c || t == null || t === "" ? (this._$AH !== c && this._$AR(), this._$AH = c) : t !== this._$AH && t !== T && this._(t) : t._$litType$ !== void 0 ? this.$(t) : t.nodeType !== void 0 ? this.T(t) : Kt(t) ? this.k(t) : this._(t);
  }
  O(t) {
    return this._$AA.parentNode.insertBefore(t, this._$AB);
  }
  T(t) {
    this._$AH !== t && (this._$AR(), this._$AH = this.O(t));
  }
  _(t) {
    this._$AH !== c && U(this._$AH) ? this._$AA.nextSibling.data = t : this.T(S.createTextNode(t)), this._$AH = t;
  }
  $(t) {
    const { values: e, _$litType$: s } = t, i = typeof s == "number" ? this._$AC(t) : (s.el === void 0 && (s.el = I.createElement(Mt(s.h, s.h[0]), this.options)), s);
    if (this._$AH?._$AD === i) this._$AH.p(e);
    else {
      const a = new Yt(i, this), n = a.u(this.options);
      a.p(e), this.T(n), this._$AH = a;
    }
  }
  _$AC(t) {
    let e = $t.get(t.strings);
    return e === void 0 && $t.set(t.strings, e = new I(t)), e;
  }
  k(t) {
    ot(this._$AH) || (this._$AH = [], this._$AR());
    const e = this._$AH;
    let s, i = 0;
    for (const a of t) i === e.length ? e.push(s = new H(this.O(z()), this.O(z()), this, this.options)) : s = e[i], s._$AI(a), i++;
    i < e.length && (this._$AR(s && s._$AB.nextSibling, i), e.length = i);
  }
  _$AR(t = this._$AA.nextSibling, e) {
    for (this._$AP?.(!1, !0, e); t !== this._$AB; ) {
      const s = ut(t).nextSibling;
      ut(t).remove(), t = s;
    }
  }
  setConnected(t) {
    this._$AM === void 0 && (this._$Cv = t, this._$AP?.(t));
  }
}
class Y {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(t, e, s, i, a) {
    this.type = 1, this._$AH = c, this._$AN = void 0, this.element = t, this.name = e, this._$AM = i, this.options = a, s.length > 2 || s[0] !== "" || s[1] !== "" ? (this._$AH = Array(s.length - 1).fill(new String()), this.strings = s) : this._$AH = c;
  }
  _$AI(t, e = this, s, i) {
    const a = this.strings;
    let n = !1;
    if (a === void 0) t = C(this, t, e, 0), n = !U(t) || t !== this._$AH && t !== T, n && (this._$AH = t);
    else {
      const o = t;
      let d, u;
      for (t = a[0], d = 0; d < a.length - 1; d++) u = C(this, o[s + d], e, d), u === T && (u = this._$AH[d]), n ||= !U(u) || u !== this._$AH[d], u === c ? t = c : t !== c && (t += (u ?? "") + a[d + 1]), this._$AH[d] = u;
    }
    n && !i && this.j(t);
  }
  j(t) {
    t === c ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, t ?? "");
  }
}
class Jt extends Y {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(t) {
    this.element[this.name] = t === c ? void 0 : t;
  }
}
class Zt extends Y {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(t) {
    this.element.toggleAttribute(this.name, !!t && t !== c);
  }
}
class Gt extends Y {
  constructor(t, e, s, i, a) {
    super(t, e, s, i, a), this.type = 5;
  }
  _$AI(t, e = this) {
    if ((t = C(this, t, e, 0) ?? c) === T) return;
    const s = this._$AH, i = t === c && s !== c || t.capture !== s.capture || t.once !== s.once || t.passive !== s.passive, a = t !== c && (s === c || i);
    i && this.element.removeEventListener(this.name, this, s), a && this.element.addEventListener(this.name, this, t), this._$AH = t;
  }
  handleEvent(t) {
    typeof this._$AH == "function" ? this._$AH.call(this.options?.host ?? this.element, t) : this._$AH.handleEvent(t);
  }
}
class Xt {
  constructor(t, e, s) {
    this.element = t, this.type = 6, this._$AN = void 0, this._$AM = e, this.options = s;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(t) {
    C(this, t);
  }
}
const Qt = rt.litHtmlPolyfillSupport;
Qt?.(I, H), (rt.litHtmlVersions ??= []).push("3.3.3");
const te = (r, t, e) => {
  const s = e?.renderBefore ?? t;
  let i = s._$litPart$;
  if (i === void 0) {
    const a = e?.renderBefore ?? null;
    s._$litPart$ = i = new H(t.insertBefore(z(), a), a, void 0, e ?? {});
  }
  return i._$AI(r), i;
};
const nt = globalThis;
class $ extends E {
  constructor() {
    super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
  }
  createRenderRoot() {
    const t = super.createRenderRoot();
    return this.renderOptions.renderBefore ??= t.firstChild, t;
  }
  update(t) {
    const e = this.render();
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(t), this._$Do = te(e, this.renderRoot, this.renderOptions);
  }
  connectedCallback() {
    super.connectedCallback(), this._$Do?.setConnected(!0);
  }
  disconnectedCallback() {
    super.disconnectedCallback(), this._$Do?.setConnected(!1);
  }
  render() {
    return T;
  }
}
$._$litElement$ = !0, $.finalized = !0, nt.litElementHydrateSupport?.({ LitElement: $ });
const ee = nt.litElementPolyfillSupport;
ee?.({ LitElement: $ });
(nt.litElementVersions ??= []).push("4.2.2");
const b = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday"
], D = [15, 30, 60, 120], k = {
  monday: "Mon",
  tuesday: "Tue",
  wednesday: "Wed",
  thursday: "Thu",
  friday: "Fri",
  saturday: "Sat",
  sunday: "Sun"
};
function yt(r = /* @__PURE__ */ new Date()) {
  return b[(r.getDay() + 6) % 7];
}
function se() {
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
function f(r) {
  return r.slice(0, 5);
}
function m(r, t = !1) {
  const [e, s] = f(r).split(":").map(Number), i = e * 60 + s;
  return t && i === 0 ? 1440 : i;
}
function vt(r, t = !1) {
  return t && m(r, !0) === 1440 ? "24:00:00" : `${f(r)}:00`;
}
function g(r) {
  if (r.trim() === "") return;
  const t = Number(r);
  return Number.isFinite(t) ? t : void 0;
}
function xt(r) {
  const t = {};
  r.hvac_mode && (t.hvac_mode = r.hvac_mode), r.fan_mode && (t.fan_mode = r.fan_mode);
  const e = g(r.temperature);
  e !== void 0 && (t.temperature = e);
  const s = g(r.target_temp_low), i = g(r.target_temp_high);
  s !== void 0 && (t.target_temp_low = s), i !== void 0 && (t.target_temp_high = i);
  const a = g(r.humidity);
  a !== void 0 && (t.humidity = a);
  const n = {
    from: vt(r.from),
    to: vt(r.to, !0)
  };
  return Object.keys(t).length > 0 && (n.data = t), n;
}
function wt(r, t) {
  const e = r.data ?? {}, s = (i) => e[i] === void 0 ? "" : String(e[i]);
  return {
    index: t,
    origin: B(r),
    from: f(r.from),
    to: f(r.to) === "24:00" ? "00:00" : f(r.to),
    hvac_mode: s("hvac_mode"),
    temperature: s("temperature"),
    target_temp_low: s("target_temp_low"),
    target_temp_high: s("target_temp_high"),
    fan_mode: s("fan_mode"),
    humidity: s("humidity")
  };
}
function ie(r, t) {
  if (!r.from || !r.to) return "Set a start and end time";
  const e = m(r.from), s = m(r.to, !0);
  if (s <= e) return "The end time must be after the start time";
  const i = g(r.target_temp_low), a = g(r.target_temp_high);
  return i === void 0 != (a === void 0) ? "A temperature range needs both a low and a high value" : i !== void 0 && a !== void 0 && i >= a ? "The low temperature must be below the high temperature" : g(r.temperature) !== void 0 && i !== void 0 ? "Set either a target temperature or a temperature range" : t.some((o, d) => d === r.index ? !1 : e < m(o.to, !0) && s > m(o.from)) ? "This block overlaps another block on the same day" : null;
}
function A(r) {
  return [...r].sort((t, e) => m(t.from) - m(e.from));
}
function kt(r, t, e) {
  return { ...r, [t]: A(e) };
}
function ae(r) {
  const t = {
    type: "schedule/update",
    schedule_id: r.id,
    name: r.name
  };
  r.icon && (t.icon = r.icon);
  for (const e of b)
    t[e] = A(r[e] ?? []);
  return t;
}
function Dt(r) {
  const t = r.data ?? {}, e = [];
  return t.hvac_mode !== void 0 && e.push(String(t.hvac_mode).replaceAll("_", " ")), t.temperature !== void 0 && e.push(`${t.temperature}°`), t.target_temp_low !== void 0 && t.target_temp_high !== void 0 && e.push(`${t.target_temp_low}° – ${t.target_temp_high}°`), t.fan_mode !== void 0 && e.push(`fan ${t.fan_mode}`), t.humidity !== void 0 && e.push(`${t.humidity}%`), e.length > 0 ? e.join(" · ") : "No changes";
}
const Z = {
  all: [...b],
  weekdays: ["monday", "tuesday", "wednesday", "thursday", "friday"],
  weekend: ["saturday", "sunday"]
};
function B(r) {
  const t = { from: r.from, to: r.to };
  return r.data && (t.data = { ...r.data }), t;
}
function re(r, t) {
  const e = Object.keys(r ?? {}).sort(), s = Object.keys(t ?? {}).sort();
  return e.length !== s.length ? !1 : e.every(
    (i, a) => i === s[a] && r?.[i] === t?.[i]
  );
}
function oe(r, t) {
  return r.from === t.from && r.to === t.to && re(r.data, t.data);
}
function At(r, t) {
  return t ? r.findIndex((e) => oe(e, t)) : -1;
}
function ne(r, t) {
  return m(r.from) < m(t.to, !0) && m(r.to, !0) > m(t.from);
}
function le(r, t, e, s) {
  const i = { ...t }, a = [], n = A(r);
  for (const o of e) {
    if (s === "replace") {
      i[o] = n.map(B);
      continue;
    }
    const u = A(i[o] ?? t[o] ?? []).map(B);
    let h = !1;
    for (const p of n) {
      if (u.some((_) => ne(p, _))) {
        h = !0;
        continue;
      }
      u.push(B(p));
    }
    i[o] = A(u), h && a.push(o);
  }
  return { schedule: i, conflicts: a };
}
const j = class j extends $ {
  setConfig(t) {
    this._config = { ...t };
  }
  _setValue(t, e) {
    if (!this._config) return;
    const s = { ...this._config, [t]: e };
    this._config = s, this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: s },
        bubbles: !0,
        composed: !0
      })
    );
  }
  render() {
    if (!this.hass || !this._config) return c;
    const t = Object.values(this.hass.states).filter(
      (s) => s.entity_id.startsWith("climate.") && "schedule_enabled" in s.attributes
    ), e = (this._config.timer_presets ?? D).join(", ");
    return l`
      <div class="form">
        <label>
          Entity
          <select
            .value=${this._config.entity ?? ""}
            @change=${(s) => this._setValue("entity", s.target.value)}
          >
            <option value="" disabled>Select an entity</option>
            ${t.map(
      (s) => l`
                <option value=${s.entity_id}>
                  ${s.attributes.friendly_name ?? s.entity_id}
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
            @input=${(s) => this._setValue("name", s.target.value)}
          />
        </label>
        <label>
          Layout
          <select
            name="layout"
            .value=${this._config.layout ?? "standard"}
            @change=${(s) => this._setValue(
      "layout",
      s.target.value
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
            @change=${(s) => this._setValue(
      "show_schedule",
      s.target.checked
    )}
          />
          Show schedule controls
        </label>
        <label class="toggle">
          <input
            type="checkbox"
            .checked=${this._config.show_plan !== !1}
            @change=${(s) => this._setValue(
      "show_plan",
      s.target.checked
    )}
          />
          Show plan selector
        </label>
        <label class="toggle">
          <input
            type="checkbox"
            .checked=${this._config.show_override !== !1}
            @change=${(s) => this._setValue(
      "show_override",
      s.target.checked
    )}
          />
          Show hold (override) button
        </label>
        <label>
          Default plan
          <input
            type="text"
            .value=${this._config.default_plan ?? ""}
            @input=${(s) => this._setValue(
      "default_plan",
      s.target.value || void 0
    )}
          />
        </label>
        <label class="toggle">
          <input
            type="checkbox"
            .checked=${this._config.schedule_editable !== !1}
            @change=${(s) => this._setValue(
      "schedule_editable",
      s.target.checked
    )}
          />
          Allow editing the schedule
        </label>
        <label>
          Day shown first
          <select
            name="default_schedule_day"
            .value=${this._config.default_schedule_day ?? ""}
            @change=${(s) => this._setValue(
      "default_schedule_day",
      s.target.value || void 0
    )}
          >
            <option value="">Today</option>
            ${b.map(
      (s) => l`<option value=${s}>${k[s]}</option>`
    )}
          </select>
        </label>
        <label class="toggle">
          <input
            type="checkbox"
            .checked=${this._config.show_timer !== !1}
            @change=${(s) => this._setValue(
      "show_timer",
      s.target.checked
    )}
          />
          Show timer controls
        </label>
        <label>
          Timer presets (minutes)
          <input
            type="text"
            .value=${e}
            @change=${(s) => {
      const i = s.target.value.split(",").map((a) => Number.parseInt(a.trim(), 10)).filter((a) => Number.isFinite(a) && a > 0);
      this._setValue("timer_presets", i.length ? i : D);
    }}
          />
        </label>
      </div>
    `;
  }
};
j.properties = {
  hass: { attribute: !1 },
  _config: { state: !0 }
}, j.styles = P`
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
let X = j;
customElements.get("scheduled-climate-card-editor") || customElements.define("scheduled-climate-card-editor", X);
const St = 1440, ce = [0, 6, 12, 18, 24];
function de(r) {
  return A(r).map((e, s) => {
    const i = m(e.from), a = m(e.to, !0);
    return {
      from: e.from,
      to: e.to,
      startPercent: i / St * 100,
      widthPercent: Math.max(0, a - i) / St * 100,
      index: s,
      label: Dt(e)
    };
  });
}
function he(r) {
  const t = {};
  for (const e of b)
    t[e] = de(r[e] ?? []);
  return t;
}
const lt = P`
  ha-dialog {
    --mdc-dialog-min-width: min(560px, 92vw);
    --mdc-dialog-max-width: min(640px, 96vw);
  }
  .content {
    display: grid;
    gap: 16px;
    color: var(--primary-text-color);
  }
  /* Home Assistant's ha-dialog does not reliably render its own heading text
     across versions, so each dialog draws its own title row. */
  .dialog-title {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .dialog-title h2 {
    margin: 0;
    flex: 1;
    font-size: var(--ha-font-size-xl, 20px);
    font-weight: 500;
    color: var(--primary-text-color);
  }
  h4 {
    margin: 0;
    font-size: var(--ha-font-size-m, 14px);
  }
  p,
  .caption,
  .field > span {
    margin: 0;
    color: var(--secondary-text-color);
    font-size: 12px;
  }
  .tabs,
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }
  .field {
    display: grid;
    gap: 5px;
  }
  label.field > span {
    font-size: 12px;
  }
  button {
    min-height: 40px;
    padding: 8px 12px;
    border: 1px solid var(--divider-color);
    border-radius: var(--ha-border-radius-pill, 999px);
    color: var(--primary-text-color);
    background: var(--card-background-color);
    font: inherit;
    cursor: pointer;
    text-transform: capitalize;
    white-space: nowrap;
  }
  button:hover {
    background: color-mix(in srgb, var(--primary-color) 8%, var(--card-background-color));
  }
  button.selected,
  button.primary {
    color: var(--text-primary-color, white);
    background: var(--primary-color);
    border-color: var(--primary-color);
  }
  button:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
  button.icon {
    width: 40px;
    padding: 7px;
  }
  button ha-icon {
    --mdc-icon-size: 18px;
    margin-right: 6px;
    vertical-align: -4px;
  }
  button.icon ha-icon {
    margin: 0;
  }
  input,
  select {
    box-sizing: border-box;
    min-width: 0;
    min-height: 40px;
    padding: 7px 10px;
    color: var(--primary-text-color);
    background: var(--card-background-color);
    border: 1px solid var(--divider-color);
    border-radius: var(--ha-border-radius-md, 8px);
    font: inherit;
  }
  input[type="checkbox"],
  input[type="radio"] {
    min-height: 0;
    accent-color: var(--primary-color);
  }
  .radios {
    display: flex;
    gap: 16px;
  }
  .radios label,
  .day-checks label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    text-transform: none;
  }
  .day-checks {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 8px;
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .error {
    color: var(--error-color, #db4437);
    font-size: 12px;
  }
  .warning {
    color: var(--warning-color, #ffa600);
    font-size: 12px;
  }
`, V = class V extends $ {
  constructor() {
    super(...arguments), this.open = !1, this.sourceDay = "monday", this.roomEntities = [], this.planOptions = [], this.currentEntityId = "", this.currentPlan = "", this._selected = /* @__PURE__ */ new Set(), this._mode = "replace", this._destKey = "", this._wasOpen = !1;
  }
  willUpdate(t) {
    t.has("open") && this.open && !this._wasOpen && (this._selected = /* @__PURE__ */ new Set(), this._mode = "replace", this._destKey = `${this.currentEntityId}::${this.currentPlan}`), this._wasOpen = this.open;
  }
  _destinations() {
    const t = [];
    for (const e of this.roomEntities) {
      const s = this.hass?.states[e]?.attributes, i = s?.friendly_name ?? e, a = s?.plan_schedules ?? {}, n = s?.plan_options ?? this.planOptions;
      for (const o of n) {
        const d = this.roomEntities.length <= 1, u = e === this.currentEntityId && o === this.currentPlan, h = d ? u ? `${o} (this schedule)` : o : `${i} · ${o}${u ? " (this schedule)" : ""}`;
        t.push({
          entityId: e,
          plan: o,
          label: h,
          disabled: !u && !a[o]
        });
      }
    }
    return t;
  }
  _close() {
    this.open = !1, this.dispatchEvent(
      new CustomEvent("dialog-closed", { bubbles: !0, composed: !0 })
    );
  }
  _toggleDay(t, e) {
    const s = new Set(this._selected);
    e ? s.add(t) : s.delete(t), this._selected = s;
  }
  _pick(t) {
    this._selected = new Set(t.filter((e) => e !== this.sourceDay));
  }
  _confirm() {
    const t = b.filter((i) => this._selected.has(i));
    if (t.length === 0) return;
    const [e, s] = this._destKey.split("::");
    this.dispatchEvent(
      new CustomEvent("copy", {
        bubbles: !0,
        composed: !0,
        detail: { targetDays: t, mode: this._mode, destination: { entityId: e, plan: s } }
      })
    ), this._close();
  }
  render() {
    if (!this.open) return c;
    const t = this._destinations();
    return l`
      <ha-dialog open @closed=${this._close}>
        <div class="content">
          <div class="dialog-title">
            <h2>Copy ${k[this.sourceDay]}</h2>
          </div>
          <div class="field">
            <span>Copy to days</span>
            <div class="chips">
              <button @click=${() => this._pick(Z.all)}>All</button>
              <button @click=${() => this._pick(Z.weekdays)}>Weekdays</button>
              <button @click=${() => this._pick(Z.weekend)}>Weekend</button>
              <button @click=${() => this._selected = /* @__PURE__ */ new Set()}>Clear</button>
            </div>
            <div class="day-checks">
              ${b.map(
      (e) => l`
                  <label>
                    <input
                      type="checkbox"
                      ?disabled=${e === this.sourceDay}
                      .checked=${this._selected.has(e)}
                      @change=${(s) => this._toggleDay(
        e,
        s.target.checked
      )}
                    />
                    ${k[e]}
                  </label>
                `
    )}
            </div>
          </div>

          <div class="field">
            <span>How should existing blocks be handled?</span>
            <div class="radios">
              <label>
                <input
                  type="radio"
                  name="copy-mode"
                  ?checked=${this._mode === "replace"}
                  @change=${() => this._mode = "replace"}
                />
                Replace
              </label>
              <label>
                <input
                  type="radio"
                  name="copy-mode"
                  ?checked=${this._mode === "merge"}
                  @change=${() => this._mode = "merge"}
                />
                Merge
              </label>
            </div>
          </div>

          ${t.length > 1 ? l`
                <label class="field">
                  <span>Destination schedule</span>
                  <select
                    .value=${this._destKey}
                    @change=${(e) => this._destKey = e.target.value}
                  >
                    ${t.map(
      (e) => l`<option
                        value=${`${e.entityId}::${e.plan}`}
                        ?disabled=${e.disabled}
                      >
                        ${e.label}${e.disabled ? " — no schedule" : ""}
                      </option>`
    )}
                  </select>
                </label>
              ` : c}
        </div>

        <button slot="secondaryAction" @click=${this._close}>Cancel</button>
        <button
          slot="primaryAction"
          class="primary"
          ?disabled=${this._selected.size === 0}
          @click=${this._confirm}
        >
          Copy
        </button>
      </ha-dialog>
    `;
  }
};
V.properties = {
  hass: { attribute: !1 },
  open: { attribute: !1 },
  sourceDay: { attribute: !1 },
  roomEntities: { attribute: !1 },
  planOptions: { attribute: !1 },
  currentEntityId: { attribute: !1 },
  currentPlan: { attribute: !1 },
  _selected: { state: !0 },
  _mode: { state: !0 },
  _destKey: { state: !0 }
}, V.styles = [
  lt,
  P`
      :host {
        display: contents;
      }
    `
];
let Q = V;
customElements.get("scheduled-climate-copy-dialog") || customElements.define(
  "scheduled-climate-copy-dialog",
  Q
);
const W = class W extends $ {
  constructor() {
    super(...arguments), this.open = !1, this._selectedTarget = "", this._selectedPlan = "", this._selectedDay = yt(), this._schedules = [], this._error = "", this._warning = "", this._busy = !1, this._loading = !1, this._copyOpen = !1, this._wasOpen = !1;
  }
  disconnectedCallback() {
    super.disconnectedCallback(), this._unsubscribe?.(), this._unsubscribe = void 0;
  }
  willUpdate(t) {
    t.has("open") && (this.open && !this._wasOpen && this._onOpen(), !this.open && this._wasOpen && (this._unsubscribe?.(), this._unsubscribe = void 0)), this._wasOpen = this.open;
  }
  _onOpen() {
    const t = this._roomEntities();
    this._selectedTarget = this.initialTarget && t.includes(this.initialTarget) ? this.initialTarget : this.entityId ?? t[0] ?? "";
    const e = this._planOptions(this._selectedTarget), s = this._targetState()?.attributes.active_plan ?? void 0;
    this._selectedPlan = this.initialPlan && e.includes(this.initialPlan) ? this.initialPlan : s && e.includes(s) ? s : e[0] ?? "", this._selectedDay = yt(), this._draft = void 0, this._error = "", this._warning = "", this._subscribe();
  }
  get _isAdmin() {
    return this.hass?.user?.is_admin === !0;
  }
  _roomEntities() {
    const e = (this.entityId ? this.hass?.states[this.entityId]?.attributes : void 0)?.room_entities;
    return e && e.length > 0 ? e : this.entityId ? [this.entityId] : [];
  }
  _planOptions(t) {
    return this.hass?.states[t]?.attributes.plan_options ?? [];
  }
  _targetState() {
    return this._selectedTarget ? this.hass?.states[this._selectedTarget] : void 0;
  }
  _scheduleStorageId() {
    return (this._targetState()?.attributes.plan_schedules ?? {})[this._selectedPlan] ?? null;
  }
  _schedule() {
    const t = this._scheduleStorageId();
    if (t)
      return this._schedules.find((e) => e.id === t);
  }
  async _subscribe() {
    if (this._unsubscribe?.(), this._unsubscribe = void 0, await this._loadSchedules(), !!this.hass?.connection && this.open)
      try {
        const t = await this.hass.connection.subscribeMessage(
          () => {
            this._loadSchedules();
          },
          { type: "schedule/subscribe" }
        );
        if (!this.open) {
          t();
          return;
        }
        this._unsubscribe = t;
      } catch {
      }
  }
  async _loadSchedules() {
    if (this.hass) {
      this._loading = !0;
      try {
        this._schedules = await this.hass.callWS({
          type: "schedule/list"
        });
      } catch (t) {
        this._error = t instanceof Error ? t.message : "Unable to load schedules";
      } finally {
        this._loading = !1;
      }
    }
  }
  _close() {
    this.open = !1, this.dispatchEvent(
      new CustomEvent("dialog-closed", { bubbles: !0, composed: !0 })
    );
  }
  _selectTarget(t) {
    this._selectedTarget = t;
    const e = this._planOptions(t);
    if (!e.includes(this._selectedPlan)) {
      const s = this.hass?.states[t]?.attributes.active_plan;
      this._selectedPlan = s && e.includes(s) ? s : e[0] ?? "";
    }
    this._draft = void 0, this._error = "", this._warning = "";
  }
  _selectPlan(t) {
    this._selectedPlan = t, this._draft = void 0, this._error = "", this._warning = "";
  }
  _selectDay(t) {
    this._selectedDay = t, this._draft = void 0, this._error = "";
  }
  _dayBlocks(t = this._selectedDay) {
    return A(this._schedule()?.[t] ?? []);
  }
  async _writeSchedule(t) {
    if (!this.hass || this._busy || !this._isAdmin) return !1;
    this._busy = !0, this._error = "";
    try {
      return await this.hass.callWS(ae(t)), this._schedules = this._schedules.map(
        (e) => e.id === t.id ? t : e
      ), !0;
    } catch (e) {
      return this._error = e instanceof Error ? e.message : "Unable to save the schedule", !1;
    } finally {
      this._busy = !1;
    }
  }
  async _saveDraft() {
    const t = this._draft, e = this._schedule();
    if (!e || !t) return;
    const s = this._dayBlocks();
    let i = null;
    if (t.origin && (i = At(s, t.origin), i < 0)) {
      this._error = "That block changed somewhere else. Reopen it and try again.", this._draft = void 0;
      return;
    }
    const a = { ...t, index: i }, n = ie(a, s);
    if (n) {
      this._error = n;
      return;
    }
    const o = [...s];
    i === null ? o.push(xt(a)) : o[i] = xt(a), await this._writeSchedule(kt(e, this._selectedDay, o)) && (this._draft = void 0);
  }
  _duplicateBlock(t) {
    this._draft = { ...wt(t, 0), index: null, origin: void 0 }, this._error = "";
  }
  async _deleteBlock(t) {
    const e = this._schedule();
    if (!e) return;
    const s = this._dayBlocks(), i = At(s, t);
    if (i < 0) {
      this._error = "That block changed somewhere else. Reopen it and try again.";
      return;
    }
    const a = s.filter((n, o) => o !== i);
    this._draft = void 0, await this._writeSchedule(kt(e, this._selectedDay, a));
  }
  _openBlock(t, e) {
    if (this._selectedDay = t, !this._isAdmin) {
      this._draft = void 0;
      return;
    }
    const s = this._dayBlocks(t)[e];
    this._draft = s ? wt(s, e) : void 0, this._error = "";
  }
  _openEmptyDay(t) {
    this._selectedDay = t, this._isAdmin && (this._draft = { ...se(), index: null }, this._error = "");
  }
  async _createSchedule() {
    const t = this._targetState();
    if (!this.hass || !t || this._busy || !this._isAdmin) return;
    const e = {
      type: "schedule/create",
      name: `${t.attributes.friendly_name ?? this._selectedTarget} — ${this._selectedPlan}`
    };
    for (const i of b) e[i] = [];
    this._busy = !0, this._error = "";
    let s;
    try {
      s = await this.hass.callWS(e);
    } catch (i) {
      this._error = i instanceof Error ? i.message : "Unable to create the schedule";
    } finally {
      this._busy = !1;
    }
    if (s)
      try {
        await this.hass.callService("scheduled_climate", "link_schedule", {
          entity_id: this._selectedTarget,
          schedule_id: s.id,
          plan: this._selectedPlan
        }), await this._loadSchedules();
      } catch (i) {
        this._error = i instanceof Error ? i.message : "Unable to link the schedule";
      }
  }
  async _onCopy(t) {
    this._copyOpen = !1;
    const { targetDays: e, mode: s, destination: i } = t.detail, a = this._dayBlocks(), o = this.hass?.states[i.entityId]?.attributes?.plan_schedules?.[i.plan] ?? null, d = o === this._scheduleStorageId() ? this._schedule() : this._schedules.find((p) => p.id === o);
    if (!d) {
      this._error = "That schedule is not available yet.";
      return;
    }
    const { schedule: u, conflicts: h } = le(
      a,
      d,
      e,
      s
    );
    this._warning = "", await this._writeSchedule(u) && h.length > 0 && (this._warning = `Some blocks were skipped to avoid overlaps on ${h.map((p) => k[p]).join(", ")}.`);
  }
  _renderTimeline(t) {
    const e = he(t);
    return l`
      <div class="timeline" role="grid" aria-label="Weekly schedule">
        <div class="axis">
          <span class="axis-label"></span>
          <div class="ticks">
            ${ce.map(
      (s) => l`<span
                class="tick"
                style="left:${s / 24 * 100}%"
                >${s}</span
              >`
    )}
          </div>
        </div>
        ${b.map(
      (s) => l`
            <div class="row" role="row">
              <button
                class=${`day-name ${s === this._selectedDay ? "selected" : ""}`}
                @click=${() => this._selectDay(s)}
              >
                ${k[s]}
              </button>
              <div
                class="track"
                @click=${() => this._openEmptyDay(s)}
              >
                ${e[s].map(
        (i) => l`<button
                    class="segment"
                    title=${`${f(i.from)} – ${f(i.to)} · ${i.label}`}
                    style="left:${i.startPercent}%;width:${i.widthPercent}%"
                    @click=${(a) => {
          a.stopPropagation(), this._openBlock(s, i.index);
        }}
                  >
                    <span>${f(i.from)}</span>
                  </button>`
      )}
              </div>
            </div>
          `
    )}
      </div>
    `;
  }
  _renderBlockList(t) {
    const e = this._dayBlocks();
    return l`
      <div class="day-chips" role="tablist" aria-label="Days of the week">
        ${b.map(
      (s) => l`
            <button
              role="tab"
              aria-selected=${s === this._selectedDay}
              class=${s === this._selectedDay ? "selected" : ""}
              @click=${() => this._selectDay(s)}
            >
              ${k[s]}
            </button>
          `
    )}
      </div>
      <ul class="block-list">
        ${e.length === 0 ? l`<li class="caption">No blocks on ${k[this._selectedDay]}</li>` : e.map(
      (s, i) => l`
                <li class="block">
                  <div class="block-copy">
                    <span>${f(s.from)} – ${f(s.to)}</span>
                    <small>${Dt(s)}</small>
                  </div>
                  ${this._isAdmin ? l`
                        <button class="icon" title="Edit block" aria-label="Edit block" @click=${() => this._openBlock(this._selectedDay, i)}>
                          <ha-icon icon="mdi:pencil-outline"></ha-icon>
                        </button>
                        <button class="icon" title="Duplicate block" aria-label="Duplicate block" @click=${() => this._duplicateBlock(s)}>
                          <ha-icon icon="mdi:content-duplicate"></ha-icon>
                        </button>
                        <button class="icon" title="Delete block" aria-label="Delete block" @click=${() => this._deleteBlock(s)}>
                          <ha-icon icon="mdi:delete-outline"></ha-icon>
                        </button>
                      ` : c}
                </li>
              `
    )}
      </ul>
      ${this._isAdmin ? l`
            <div class="actions">
              <button class="primary" ?disabled=${this._busy} @click=${() => this._openEmptyDay(this._selectedDay)}>
                <ha-icon icon="mdi:plus"></ha-icon>Add block
              </button>
              <button ?disabled=${this._busy || this._dayBlocks().length === 0} @click=${() => this._copyOpen = !0}>
                <ha-icon icon="mdi:content-copy"></ha-icon>Copy day
              </button>
            </div>
            ${this._draft ? this._renderDraft(t, this._draft) : c}
          ` : c}
    `;
  }
  _renderDraft(t, e) {
    const s = t.attributes, i = s.supported_features ?? 0, a = (o) => {
      this._draft = { ...this._draft ?? e, ...o };
    }, n = (o) => o.target.value;
    return l`
      <div class="grid draft">
        <label class="field"><span>From</span><input type="time" .value=${e.from} @input=${(o) => a({ from: n(o) })} /></label>
        <label class="field"><span>To</span><input type="time" .value=${e.to} @input=${(o) => a({ to: n(o) })} /></label>
        <label class="field">
          <span>Mode</span>
          <select .value=${e.hvac_mode} @change=${(o) => a({ hvac_mode: n(o) })}>
            <option value="">Unchanged</option>
            ${(s.hvac_modes ?? []).map(
      (o) => l`<option value=${o} ?selected=${o === e.hvac_mode}>${o.replaceAll("_", " ")}</option>`
    )}
          </select>
        </label>
        ${i & 8 && (s.fan_modes ?? []).length > 0 ? l`
              <label class="field">
                <span>Fan</span>
                <select .value=${e.fan_mode} @change=${(o) => a({ fan_mode: n(o) })}>
                  <option value="">Unchanged</option>
                  ${(s.fan_modes ?? []).map(
      (o) => l`<option value=${o} ?selected=${o === e.fan_mode}>${o}</option>`
    )}
                </select>
              </label>
            ` : c}
        ${i & 1 ? l`<label class="field"><span>Temperature</span><input type="number" min=${s.min_temp ?? 7} max=${s.max_temp ?? 35} step=${s.target_temp_step ?? 0.5} .value=${e.temperature} @input=${(o) => a({ temperature: n(o) })} /></label>` : c}
        ${i & 2 ? l`
              <label class="field"><span>Low</span><input type="number" min=${s.min_temp ?? 7} max=${s.max_temp ?? 35} step=${s.target_temp_step ?? 0.5} .value=${e.target_temp_low} @input=${(o) => a({ target_temp_low: n(o) })} /></label>
              <label class="field"><span>High</span><input type="number" min=${s.min_temp ?? 7} max=${s.max_temp ?? 35} step=${s.target_temp_step ?? 0.5} .value=${e.target_temp_high} @input=${(o) => a({ target_temp_high: n(o) })} /></label>
            ` : c}
        ${i & 4 ? l`<label class="field"><span>Humidity</span><input type="number" min=${s.min_humidity ?? 30} max=${s.max_humidity ?? 99} step="1" .value=${e.humidity} @input=${(o) => a({ humidity: n(o) })} /></label>` : c}
        <div class="actions draft-actions">
          <button class="primary" ?disabled=${this._busy} @click=${() => this._saveDraft()}><ha-icon icon="mdi:content-save-outline"></ha-icon>Save block</button>
          <button ?disabled=${this._busy} @click=${() => this._draft = void 0}>Cancel</button>
        </div>
      </div>
    `;
  }
  _renderMissing() {
    return this._isAdmin ? l`
        <div class="missing">
          <p class="caption">No schedule is linked to the “${this._selectedPlan}” plan for this target yet.</p>
          <button class="primary" ?disabled=${this._busy} @click=${() => this._createSchedule()}>
            <ha-icon icon="mdi:calendar-plus"></ha-icon>Create schedule for this plan
          </button>
        </div>
      ` : l`<p class="caption">No schedule is linked to the “${this._selectedPlan}” plan yet. Ask an administrator to create one.</p>`;
  }
  render() {
    if (!this.open || !this.hass) return c;
    const t = this._roomEntities(), e = this._targetState(), s = this._planOptions(this._selectedTarget), i = this._schedule();
    return l`
      <ha-dialog open @closed=${this._close}>
        <div class="content">
          <div class="dialog-title">
            <h2>Schedule</h2>
          </div>
          ${s.length > 0 ? l`<div class="tabs" role="tablist" aria-label="Plans">
                ${s.map(
      (a) => l`<button
                    role="tab"
                    aria-selected=${a === this._selectedPlan}
                    class=${a === this._selectedPlan ? "selected" : ""}
                    @click=${() => this._selectPlan(a)}
                  >${a}</button>`
    )}
              </div>` : c}
          ${t.length > 1 ? l`<div class="tabs" role="tablist" aria-label="Targets">
                ${t.map(
      (a) => l`<button
                    role="tab"
                    aria-selected=${a === this._selectedTarget}
                    class=${`ghost ${a === this._selectedTarget ? "selected" : ""}`}
                    @click=${() => this._selectTarget(a)}
                  >${this.hass?.states[a]?.attributes.friendly_name ?? a}</button>`
    )}
              </div>` : c}

          ${i && e ? l`${this._renderTimeline(i)} ${this._renderBlockList(e)}` : this._scheduleStorageId() ? l`<p class="caption">${this._loading ? "Loading the schedule…" : "The linked schedule could not be found."}</p>` : this._renderMissing()}

          ${this._error ? l`<p class="error" role="alert">${this._error}</p>` : c}
          ${this._warning ? l`<p class="warning" role="status">${this._warning}</p>` : c}
        </div>

        <button slot="primaryAction" @click=${this._close}>Close</button>
      </ha-dialog>
      <scheduled-climate-copy-dialog
        .hass=${this.hass}
        .open=${this._copyOpen}
        .sourceDay=${this._selectedDay}
        .roomEntities=${t}
        .planOptions=${s}
        .currentEntityId=${this._selectedTarget}
        .currentPlan=${this._selectedPlan}
        @copy=${this._onCopy}
        @dialog-closed=${() => this._copyOpen = !1}
      ></scheduled-climate-copy-dialog>
    `;
  }
};
W.properties = {
  hass: { attribute: !1 },
  entityId: { attribute: !1 },
  open: { attribute: !1 },
  initialTarget: { attribute: !1 },
  initialPlan: { attribute: !1 },
  _selectedTarget: { state: !0 },
  _selectedPlan: { state: !0 },
  _selectedDay: { state: !0 },
  _schedules: { state: !0 },
  _draft: { state: !0 },
  _error: { state: !0 },
  _warning: { state: !0 },
  _busy: { state: !0 },
  _loading: { state: !0 },
  _copyOpen: { state: !0 }
}, W.styles = [
  lt,
  P`
      :host {
        display: contents;
      }
      .tabs button.ghost {
        text-transform: none;
      }
      .timeline {
        display: grid;
        gap: 4px;
      }
      .axis,
      .row {
        display: grid;
        grid-template-columns: 52px 1fr;
        align-items: center;
        gap: 8px;
      }
      .ticks {
        position: relative;
        height: 14px;
      }
      .tick {
        position: absolute;
        transform: translateX(-50%);
        color: var(--secondary-text-color);
        font-size: 10px;
        font-variant-numeric: tabular-nums;
      }
      .day-name {
        min-height: 34px;
        padding: 4px 6px;
        font-size: 12px;
      }
      .track {
        position: relative;
        height: 34px;
        border: 1px solid var(--divider-color);
        border-radius: var(--ha-border-radius-md, 8px);
        background: var(--secondary-background-color, color-mix(in srgb, var(--primary-text-color) 5%, var(--card-background-color)));
        overflow: hidden;
        cursor: pointer;
      }
      .segment {
        position: absolute;
        top: 3px;
        bottom: 3px;
        min-height: 0;
        min-width: 6px;
        padding: 0 4px;
        border: none;
        border-radius: 4px;
        color: var(--text-primary-color, white);
        background: var(--primary-color);
        font-size: 10px;
        text-align: left;
        overflow: hidden;
      }
      .segment span {
        pointer-events: none;
        font-variant-numeric: tabular-nums;
      }
      .day-chips {
        display: flex;
        gap: 6px;
        overflow-x: auto;
        padding-bottom: 2px;
        scrollbar-width: thin;
      }
      .day-chips button {
        flex: 1 0 auto;
        min-width: 46px;
      }
      .block-list {
        display: grid;
        gap: 8px;
        margin: 0;
        padding: 0;
        list-style: none;
      }
      .block {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        border: 1px solid var(--divider-color);
        border-radius: var(--ha-border-radius-lg, 12px);
      }
      .block-copy {
        display: grid;
        flex: 1 1 auto;
        min-width: 0;
        gap: 2px;
      }
      .block-copy span {
        font-variant-numeric: tabular-nums;
      }
      .block-copy small {
        color: var(--secondary-text-color);
        font-size: 12px;
        text-transform: capitalize;
      }
      .block .icon {
        min-height: 36px;
        padding: 6px;
      }
      .grid.draft {
        padding: 12px;
        border-radius: var(--ha-border-radius-lg, 12px);
        background: var(--secondary-background-color, color-mix(in srgb, var(--primary-text-color) 5%, var(--card-background-color)));
      }
      .draft-actions {
        grid-column: 1 / -1;
      }
      .missing {
        display: grid;
        gap: 12px;
        justify-items: start;
      }
      @media (max-width: 480px) {
        .grid.draft {
          grid-template-columns: 1fr;
        }
      }
    `
];
let tt = W;
customElements.get("scheduled-climate-schedule-dialog") || customElements.define(
  "scheduled-climate-schedule-dialog",
  tt
);
const pe = [30, 60, 120, 240];
function ue() {
  return {
    hvac_mode: "",
    temperature: "",
    target_temp_low: "",
    target_temp_high: "",
    fan_mode: "",
    humidity: ""
  };
}
const K = class K extends $ {
  constructor() {
    super(...arguments), this.open = !1, this._draft = ue(), this._durationMode = "until_next", this._minutes = 60, this._busy = !1, this._error = "", this._wasOpen = !1;
  }
  get _state() {
    return this.entityId ? this.hass?.states[this.entityId] : void 0;
  }
  willUpdate(t) {
    t.has("open") && this.open && !this._wasOpen && this._reset(), this._wasOpen = this.open;
  }
  _reset() {
    const t = this._state?.attributes, e = t?.supported_features ?? 0, s = t?.override_active ? t.override_block : null, i = (a) => a == null ? "" : String(a);
    this._draft = {
      hvac_mode: i(s?.hvac_mode),
      temperature: e & 1 ? i(s?.temperature ?? t?.temperature) : "",
      target_temp_low: e & 2 ? i(s?.target_temp_low ?? t?.target_temp_low) : "",
      target_temp_high: e & 2 ? i(s?.target_temp_high ?? t?.target_temp_high) : "",
      fan_mode: e & 8 ? i(s?.fan_mode ?? t?.fan_mode) : "",
      humidity: e & 4 ? i(s?.humidity ?? t?.humidity) : ""
    }, this._durationMode = "until_next", this._minutes = 60, this._error = "", this._busy = !1;
  }
  _close() {
    this.open = !1, this.dispatchEvent(
      new CustomEvent("dialog-closed", { bubbles: !0, composed: !0 })
    );
  }
  _update(t) {
    this._draft = { ...this._draft, ...t };
  }
  async _confirm() {
    if (!this.hass || !this.entityId || this._busy) return;
    const t = {};
    this._durationMode === "until_next" ? t.until_next_block = !0 : t.duration = { seconds: Math.max(1, Math.round(this._minutes * 60)) }, this._draft.hvac_mode && (t.hvac_mode = this._draft.hvac_mode), this._draft.fan_mode && (t.fan_mode = this._draft.fan_mode);
    const e = g(this._draft.temperature);
    e !== void 0 && (t.temperature = e);
    const s = g(this._draft.target_temp_low), i = g(this._draft.target_temp_high);
    s !== void 0 && (t.target_temp_low = s), i !== void 0 && (t.target_temp_high = i);
    const a = g(this._draft.humidity);
    a !== void 0 && (t.humidity = a), this._busy = !0, this._error = "";
    try {
      await this.hass.callService("scheduled_climate", "set_override", {
        entity_id: this.entityId,
        ...t
      }), this._close();
    } catch (n) {
      this._error = n instanceof Error ? n.message : "Command failed";
    } finally {
      this._busy = !1;
    }
  }
  async _resume() {
    if (!(!this.hass || !this.entityId || this._busy)) {
      this._busy = !0, this._error = "";
      try {
        await this.hass.callService("scheduled_climate", "clear_override", {
          entity_id: this.entityId
        }), this._close();
      } catch (t) {
        this._error = t instanceof Error ? t.message : "Command failed";
      } finally {
        this._busy = !1;
      }
    }
  }
  render() {
    if (!this.open || !this.hass) return c;
    const t = this._state;
    if (!t) return c;
    const e = t.attributes, s = e.supported_features ?? 0, i = this._draft, a = e.override_active === !0, n = (o) => o.target.value;
    return l`
      <ha-dialog open @closed=${this._close}>
        <div class="content">
          <div class="dialog-title">
            <h2>Hold temperature</h2>
          </div>
          <div class="grid">
            <label class="field">
              <span>Mode</span>
              <select
                .value=${i.hvac_mode}
                @change=${(o) => this._update({ hvac_mode: n(o) })}
              >
                <option value="">Unchanged</option>
                ${(e.hvac_modes ?? []).map(
      (o) => l`<option value=${o} ?selected=${o === i.hvac_mode}>${o.replaceAll("_", " ")}</option>`
    )}
              </select>
            </label>
            ${s & 1 ? l`<label class="field"><span>Temperature</span><input type="number" min=${e.min_temp ?? 7} max=${e.max_temp ?? 35} step=${e.target_temp_step ?? 0.5} .value=${i.temperature} @input=${(o) => this._update({ temperature: n(o) })} /></label>` : c}
            ${s & 2 ? l`
                  <label class="field"><span>Low</span><input type="number" min=${e.min_temp ?? 7} max=${e.max_temp ?? 35} step=${e.target_temp_step ?? 0.5} .value=${i.target_temp_low} @input=${(o) => this._update({ target_temp_low: n(o) })} /></label>
                  <label class="field"><span>High</span><input type="number" min=${e.min_temp ?? 7} max=${e.max_temp ?? 35} step=${e.target_temp_step ?? 0.5} .value=${i.target_temp_high} @input=${(o) => this._update({ target_temp_high: n(o) })} /></label>
                ` : c}
            ${s & 8 && (e.fan_modes ?? []).length > 0 ? l`
                  <label class="field">
                    <span>Fan</span>
                    <select .value=${i.fan_mode} @change=${(o) => this._update({ fan_mode: n(o) })}>
                      <option value="">Unchanged</option>
                      ${(e.fan_modes ?? []).map(
      (o) => l`<option value=${o} ?selected=${o === i.fan_mode}>${o}</option>`
    )}
                    </select>
                  </label>
                ` : c}
            ${s & 4 ? l`<label class="field"><span>Humidity</span><input type="number" min=${e.min_humidity ?? 30} max=${e.max_humidity ?? 99} step="1" .value=${i.humidity} @input=${(o) => this._update({ humidity: n(o) })} /></label>` : c}
          </div>

          <div class="field">
            <span>How long?</span>
            <div class="radios">
              <label>
                <input
                  type="radio"
                  name="override-duration"
                  ?checked=${this._durationMode === "until_next"}
                  @change=${() => this._durationMode = "until_next"}
                />
                Until the next scheduled change
              </label>
              <label>
                <input
                  type="radio"
                  name="override-duration"
                  ?checked=${this._durationMode === "minutes"}
                  @change=${() => this._durationMode = "minutes"}
                />
                For a set time
              </label>
            </div>
          </div>

          ${this._durationMode === "minutes" ? l`
                <div class="chips">
                  ${pe.map(
      (o) => l`<button
                      class=${this._minutes === o ? "selected" : ""}
                      @click=${() => this._minutes = o}
                    >${o < 60 ? `${o}m` : `${o / 60}h`}</button>`
    )}
                  <label class="field" style="min-width:100px">
                    <span>Minutes</span>
                    <input
                      type="number"
                      min="1"
                      step="1"
                      .value=${String(this._minutes)}
                      @input=${(o) => this._minutes = Math.max(
      1,
      Number(o.target.value)
    )}
                    />
                  </label>
                </div>
              ` : c}

          ${this._error ? l`<p class="error" role="alert">${this._error}</p>` : c}
        </div>

        ${a ? l`<button slot="secondaryAction" ?disabled=${this._busy} @click=${this._resume}>Resume schedule</button>` : l`<button slot="secondaryAction" @click=${this._close}>Cancel</button>`}
        <button slot="primaryAction" class="primary" ?disabled=${this._busy} @click=${this._confirm}>
          Hold
        </button>
      </ha-dialog>
    `;
  }
};
K.properties = {
  hass: { attribute: !1 },
  entityId: { attribute: !1 },
  open: { attribute: !1 },
  _draft: { state: !0 },
  _durationMode: { state: !0 },
  _minutes: { state: !0 },
  _busy: { state: !0 },
  _error: { state: !0 }
}, K.styles = [
  lt,
  P`
      :host {
        display: contents;
      }
    `
];
let et = K;
customElements.get("scheduled-climate-override-dialog") || customElements.define(
  "scheduled-climate-override-dialog",
  et
);
const me = /* @__PURE__ */ new Set(["unavailable", "unknown"]), _e = "scheduled-climate-card:collapsed", F = class F extends $ {
  constructor() {
    super(...arguments), this._busy = !1, this._message = "", this._timerMinutes = 30, this._selectedTarget = "", this._planMenuOpen = !1, this._scheduleOpen = !1, this._overrideOpen = !1, this._collapsed = { preset: !1, timer: !1 };
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
      show_plan: !0,
      show_override: !0,
      schedule_editable: !0,
      timer_presets: D
    };
  }
  setConfig(t) {
    if (!t.entity) throw new Error("Scheduled Climate Card requires an entity");
    this._config = {
      layout: "standard",
      show_schedule: !0,
      show_timer: !0,
      show_plan: !0,
      show_override: !0,
      schedule_editable: !0,
      timer_presets: D,
      ...t
    }, this._selectedTarget = t.entity, this._collapsed = this._loadCollapseState(t.entity);
  }
  getCardSize() {
    return 5;
  }
  get _isAdmin() {
    return this.hass?.user?.is_admin === !0;
  }
  get _state() {
    return this._config && this.hass?.states[this._config.entity];
  }
  get _roomEntities() {
    const t = this._state?.attributes.room_entities;
    return t && t.length > 0 ? t : this._config ? [this._config.entity] : [];
  }
  get _selectedState() {
    if (!this.hass || !this._config) return;
    const t = this._roomEntities, e = this._selectedTarget && t.includes(this._selectedTarget) ? this._selectedTarget : this._config.entity;
    return this.hass.states[e];
  }
  get _selectedId() {
    return this._selectedState?.entity_id ?? this._config?.entity ?? "";
  }
  _storageKey(t) {
    return `${_e}:${t}`;
  }
  _loadCollapseState(t) {
    const e = { preset: !1, timer: !1 };
    try {
      const s = localStorage.getItem(this._storageKey(t));
      if (!s) return e;
      const i = JSON.parse(s);
      return { preset: i.preset === !0, timer: i.timer === !0 };
    } catch {
      return e;
    }
  }
  _toggleSection(t) {
    if (this._config) {
      this._collapsed = { ...this._collapsed, [t]: !this._collapsed[t] };
      try {
        localStorage.setItem(
          this._storageKey(this._config.entity),
          JSON.stringify(this._collapsed)
        );
      } catch {
      }
    }
  }
  _renderCollapseButton(t, e, s) {
    const i = !this._collapsed[t];
    return l`
      <button
        class="collapse-button icon"
        title=${`${i ? "Collapse" : "Expand"} ${e.toLowerCase()}`}
        aria-label=${`${i ? "Collapse" : "Expand"} ${e.toLowerCase()}`}
        aria-expanded=${i}
        aria-controls=${s}
        @click=${() => this._toggleSection(t)}
      >
        <ha-icon icon=${i ? "mdi:chevron-up" : "mdi:chevron-down"}></ha-icon>
      </button>
    `;
  }
  async _call(t, e, s = {}) {
    if (!this.hass || this._busy) return !1;
    this._busy = !0, this._message = "";
    try {
      return await this.hass.callService(t, e, {
        entity_id: this._selectedId,
        ...s
      }), this._message = "Saved", !0;
    } catch (i) {
      return this._message = i instanceof Error ? i.message : "Command failed", !1;
    } finally {
      this._busy = !1;
    }
  }
  _formatValue(t, e = "") {
    return typeof t == "number" ? `${t}${e}` : "--";
  }
  _formatTime(t) {
    return new Date(t).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit"
    });
  }
  _modeIcon(t) {
    return {
      off: "mdi:power",
      heat: "mdi:fire",
      cool: "mdi:snowflake",
      heat_cool: "mdi:autorenew",
      auto: "mdi:calendar-sync",
      dry: "mdi:water-percent",
      fan_only: "mdi:fan"
    }[t] ?? "mdi:thermostat";
  }
  _adjustTemperature(t, e, s) {
    const i = this._selectedState;
    if (!i) return;
    const a = i.attributes, n = {
      [t]: Math.round((e + s) * 100) / 100
    };
    t === "target_temp_low" && (n.target_temp_high = a.target_temp_high), t === "target_temp_high" && (n.target_temp_low = a.target_temp_low), this._call("climate", "set_temperature", n);
  }
  _renderTemperatureControl(t, e, s, i, a, n, o) {
    return l`
      <div class="number-control" aria-label=${t}>
        <button
          class="step-button"
          title=${`Decrease ${t.toLowerCase()}`}
          aria-label=${`Decrease ${t.toLowerCase()}`}
          ?disabled=${this._busy || s - a < n}
          @click=${() => this._adjustTemperature(e, s, -a)}
        ><ha-icon icon="mdi:minus"></ha-icon></button>
        <div class="target-value">
          <span>${s}</span><small>${i}</small>
          <label>${t}</label>
        </div>
        <button
          class="step-button"
          title=${`Increase ${t.toLowerCase()}`}
          aria-label=${`Increase ${t.toLowerCase()}`}
          ?disabled=${this._busy || s + a > o}
          @click=${() => this._adjustTemperature(e, s, a)}
        ><ha-icon icon="mdi:plus"></ha-icon></button>
      </div>
    `;
  }
  _renderSelect(t, e, s, i, a) {
    return s?.length ? l`
      <label class="field">
        <span>${t}</span>
        <select
          .value=${e ?? ""}
          ?disabled=${this._busy}
          @change=${(n) => this._call("climate", i, {
      [a]: n.target.value
    })}
        >
          ${s.map((n) => l`<option value=${n}>${n.replaceAll("_", " ")}</option>`)}
        </select>
      </label>
    ` : c;
  }
  _renderTargetChips() {
    const t = this._roomEntities;
    return t.length <= 1 ? c : l`
      <div class="target-chips" role="tablist" aria-label="Room targets">
        ${t.map((e) => {
      const i = this.hass?.states[e]?.attributes.friendly_name ?? e, a = e === this._selectedId;
      return l`<button
            role="tab"
            aria-selected=${a}
            class=${a ? "selected" : ""}
            @click=${() => this._selectTarget(e)}
          >${i}</button>`;
    })}
      </div>
    `;
  }
  _selectTarget(t) {
    this._selectedTarget = t, this._planMenuOpen = !1, this._message = "";
  }
  _renderPlanChip(t) {
    if (this._config?.show_plan === !1) return c;
    const e = t.attributes, s = e.plan_options ?? [];
    if (s.length === 0) return c;
    const i = e.active_plan ?? "—", a = e.plan_resolved_automatically === !0, n = e.plan_selection_mode !== "manual";
    return l`
      <div class="plan-chip">
        <button
          class="chip"
          aria-haspopup="menu"
          aria-expanded=${this._planMenuOpen}
          ?disabled=${this._busy}
          @click=${() => this._planMenuOpen = !this._planMenuOpen}
        >
          <ha-icon icon="mdi:calendar-star"></ha-icon>
          <span>${i}</span>
          ${a ? l`<small class="auto-badge">Auto</small>` : c}
          <ha-icon icon="mdi:menu-down"></ha-icon>
        </button>
        ${this._planMenuOpen ? l`<ul class="plan-menu" role="menu">
              ${n ? l`<li role="menuitem">
                    <button
                      class=${a ? "selected" : ""}
                      @click=${() => this._selectPlan("automatic")}
                    >Automatic</button>
                  </li>` : c}
              ${s.map(
      (o) => l`<li role="menuitem">
                  <button
                    class=${!a && o === e.active_plan ? "selected" : ""}
                    @click=${() => this._selectPlan(o)}
                  >${o}</button>
                </li>`
    )}
            </ul>` : c}
      </div>
    `;
  }
  _selectPlan(t) {
    this._planMenuOpen = !1, this._call("scheduled_climate", "select_plan", { plan: t });
  }
  _renderClimate(t) {
    const e = t.attributes, s = String(e.unit_of_measurement ?? "°"), i = e.hvac_modes ?? [], a = e.temperature, n = e.target_temp_low, o = e.target_temp_high, d = e.target_temp_step ?? 0.5, u = this._config?.layout === "compact";
    return l`
      <section class="climate" aria-label="Climate controls">
        ${u ? l`<div class="compact-status">
              <div>
                <span class="current-label">Current</span>
                <span class="compact-current">${this._formatValue(e.current_temperature, s)}</span>
              </div>
              ${e.hvac_action ? l`<span class="action"><span class="pulse"></span>${e.hvac_action.replaceAll("_", " ")}</span>` : c}
            </div>` : l`<div class=${`thermostat ${t.state === "off" ? "is-off" : "is-active"}`}>
              <div class="dial-ring">
                <div class="dial-content">
                  <span class="current-label">Current</span>
                  <span class="current">${this._formatValue(e.current_temperature, s)}</span>
                  ${e.hvac_action ? l`<span class="action"><span class="pulse"></span>${e.hvac_action.replaceAll("_", " ")}</span>` : c}
                </div>
              </div>
            </div>`}
        ${typeof a == "number" ? this._renderTemperatureControl(
      "Target",
      "temperature",
      a,
      s,
      d,
      e.min_temp ?? 7,
      e.max_temp ?? 35
    ) : typeof n == "number" && typeof o == "number" ? l`<div class="range-target">
                ${this._renderTemperatureControl(
      "Low",
      "target_temp_low",
      n,
      s,
      d,
      e.min_temp ?? 7,
      o
    )}
                ${this._renderTemperatureControl(
      "High",
      "target_temp_high",
      o,
      s,
      d,
      n,
      e.max_temp ?? 35
    )}
              </div>` : c}
        <div class="modes feature-buttons" role="group" aria-label="HVAC mode">
          ${i.map(
      (h) => l`
              <button
                class=${t.state === h ? "selected" : ""}
                ?disabled=${this._busy}
                aria-pressed=${t.state === h}
                @click=${() => this._call("climate", "set_hvac_mode", { hvac_mode: h })}
              ><ha-icon icon=${this._modeIcon(h)}></ha-icon><span>${h.replaceAll("_", " ")}</span></button>
            `
    )}
        </div>
        <div class="subsection-heading">
          <div><h3>Preset & options</h3><p>${e.preset_mode?.replaceAll("_", " ") ?? "Climate settings"}</p></div>
          ${this._renderCollapseButton("preset", "Preset and options", "preset-controls")}
        </div>
        <div id="preset-controls" class="control-grid" ?hidden=${this._collapsed.preset}>
          ${this._renderSelect("Preset", e.preset_mode, e.preset_modes, "set_preset_mode", "preset_mode")}
          ${this._renderSelect("Fan", e.fan_mode, e.fan_modes, "set_fan_mode", "fan_mode")}
          ${this._renderSelect("Swing", e.swing_mode, e.swing_modes, "set_swing_mode", "swing_mode")}
          ${this._renderSelect(
      "Horizontal swing",
      e.swing_horizontal_mode,
      e.swing_horizontal_modes,
      "set_swing_horizontal_mode",
      "swing_horizontal_mode"
    )}
          ${typeof e.humidity == "number" ? l`
                <label class="field">
                  <span>Humidity</span>
                  <input
                    type="number"
                    .value=${String(e.humidity)}
                    min=${e.min_humidity ?? 30}
                    max=${e.max_humidity ?? 99}
                    ?disabled=${this._busy}
                    @change=${(h) => this._call("climate", "set_humidity", {
      humidity: Number(h.target.value)
    })}
                  />
                </label>
              ` : c}
        </div>
      </section>
    `;
  }
  _renderSchedule(t) {
    const e = t.attributes, s = e.override_active === !0, i = e.next_schedule_event, a = e.schedule_id, n = e.schedule_enabled, o = s ? e.override_until ? `Holding until ${this._formatTime(e.override_until)}` : "Holding temperature" : a ? i ? `Next change · ${new Date(i).toLocaleString()}` : n ? "No upcoming change" : "Schedule paused" : "No schedule linked";
    return l`
      <section class="summary" aria-labelledby="schedule-heading">
        <div class="section-heading">
          <ha-icon class="section-icon" icon=${s ? "mdi:gesture-tap-hold" : "mdi:calendar-clock"}></ha-icon>
          <div class="section-copy">
            <h3 id="schedule-heading">Schedule</h3>
            <p>${o}</p>
          </div>
          ${s ? l`<button
                class="icon"
                title="Resume schedule"
                aria-label="Resume schedule"
                ?disabled=${this._busy}
                @click=${() => this._call("scheduled_climate", "clear_override")}
              ><ha-icon icon="mdi:play"></ha-icon></button>` : a ? l`<button
                  class="icon"
                  title=${n ? "Pause schedule" : "Resume schedule"}
                  aria-label=${n ? "Pause schedule" : "Resume schedule"}
                  ?disabled=${this._busy}
                  @click=${() => this._call(
      "scheduled_climate",
      n ? "disable_schedule" : "enable_schedule"
    )}
                ><ha-icon icon=${n ? "mdi:pause" : "mdi:play"}></ha-icon></button>` : c}
        </div>
        <div class="summary-actions">
          <button @click=${() => this._scheduleOpen = !0}>
            <ha-icon icon="mdi:calendar-edit"></ha-icon>Edit schedule
          </button>
          ${this._config?.show_override !== !1 ? l`<button ?disabled=${this._busy} @click=${() => this._overrideOpen = !0}>
                <ha-icon icon="mdi:gesture-tap-hold"></ha-icon>Hold
              </button>` : c}
        </div>
      </section>
    `;
  }
  _renderTimer(t) {
    const e = t.attributes.timer_action, s = t.attributes.timer_deadline, i = this._config?.timer_presets ?? D;
    return l`
      <section aria-labelledby="timer-heading">
        <div class="section-heading">
          <ha-icon class="section-icon" icon="mdi:timer-outline"></ha-icon>
          <div class="section-copy"><h3 id="timer-heading">Timer</h3><p>${e && s ? `${e} at ${this._formatTime(s)}` : "No active timer"}</p></div>
          ${e ? l`<button class="icon" title="Cancel timer" aria-label="Cancel timer" @click=${() => this._call("scheduled_climate", "cancel_timer")}><ha-icon icon="mdi:timer-off-outline"></ha-icon></button>` : c}
          ${this._renderCollapseButton("timer", "Timer", "timer-controls")}
        </div>
        <div id="timer-controls" class="collapsible-body" ?hidden=${this._collapsed.timer}>
          <div class="timer-row">
            <div class="presets" aria-label="Timer presets">
              ${i.map((a) => l`<button class=${this._timerMinutes === a ? "selected" : ""} @click=${() => this._timerMinutes = a}>${a < 60 ? `${a}m` : `${a / 60}h`}</button>`)}
              <label class="custom-time"><span>Minutes</span><input type="number" min="1" step="1" .value=${String(this._timerMinutes)} @input=${(a) => this._timerMinutes = Math.max(1, Number(a.target.value))} /></label>
            </div>
            <div class="timer-actions">
              <button class="primary" ?disabled=${this._busy} @click=${() => this._startTimer("on")}><ha-icon icon="mdi:power"></ha-icon>On later</button>
              <button ?disabled=${this._busy} @click=${() => this._startTimer("off")}><ha-icon icon="mdi:power-off"></ha-icon>Off later</button>
            </div>
          </div>
        </div>
      </section>
    `;
  }
  _startTimer(t) {
    const e = Math.round(this._timerMinutes * 60);
    this._call("scheduled_climate", `start_${t}_timer`, {
      duration: { seconds: e }
    });
  }
  render() {
    if (!this._config || !this.hass) return c;
    const t = this._state;
    if (!t) return l`<ha-card><div class="empty">Entity not found</div></ha-card>`;
    const e = this._selectedState ?? t, s = me.has(e.state), i = this._config.name ?? t.attributes.friendly_name ?? "Scheduled Climate", a = this._config.default_plan ?? e.attributes.active_plan ?? void 0;
    return l`
      <ha-card class=${`state-${e.state} ${this._config.layout === "compact" ? "compact" : "standard"}`}>
        <header>
          <div class="title-block"><h2>${i}</h2><p>${s ? "Unavailable" : e.state.replaceAll("_", " ")}</p></div>
          <button class="more-info icon" title="More information" aria-label="More information" @click=${this._showMoreInfo}>
            <ha-icon icon="mdi:dots-vertical"></ha-icon>
          </button>
        </header>
        ${this._renderTargetChips()}
        ${s ? l`<div class="empty">The climate entity is unavailable.</div>` : l`
              ${this._renderClimate(e)}
              ${this._config.show_plan !== !1 ? l`<div class="plan-row">${this._renderPlanChip(e)}</div>` : c}
              ${this._config.show_schedule !== !1 ? this._renderSchedule(e) : c}
              ${this._config.show_timer !== !1 ? this._renderTimer(e) : c}
            `}
        ${this._message ? l`<div class="message" role="status">${this._message}</div>` : c}
      </ha-card>

      <scheduled-climate-schedule-dialog
        .hass=${this.hass}
        .entityId=${this._config.entity}
        .open=${this._scheduleOpen}
        .initialTarget=${this._selectedId}
        .initialPlan=${a}
        @dialog-closed=${() => this._scheduleOpen = !1}
      ></scheduled-climate-schedule-dialog>

      <scheduled-climate-override-dialog
        .hass=${this.hass}
        .entityId=${this._selectedId}
        .open=${this._overrideOpen}
        @dialog-closed=${() => this._overrideOpen = !1}
      ></scheduled-climate-override-dialog>
    `;
  }
  _showMoreInfo() {
    this.dispatchEvent(new CustomEvent("hass-more-info", {
      bubbles: !0,
      composed: !0,
      detail: { entityId: this._selectedId }
    }));
  }
};
F.properties = {
  hass: { attribute: !1 },
  _config: { state: !0 },
  _busy: { state: !0 },
  _message: { state: !0 },
  _timerMinutes: { state: !0 },
  _collapsed: { state: !0 },
  _selectedTarget: { state: !0 },
  _planMenuOpen: { state: !0 },
  _scheduleOpen: { state: !0 },
  _overrideOpen: { state: !0 }
}, F.styles = P`
    :host { display: block; color: var(--primary-text-color); --feature-color: var(--state-climate-heat-color, var(--primary-color)); }
    ha-card { overflow: visible; border-radius: var(--ha-card-border-radius, var(--ha-border-radius-lg, 12px)); }
    ha-card.state-cool { --feature-color: var(--state-climate-cool-color, #2196f3); }
    ha-card.state-dry { --feature-color: var(--state-climate-dry-color, #f9a825); }
    ha-card.state-fan_only { --feature-color: var(--state-climate-fan_only-color, #8e8e93); }
    ha-card.state-off { --feature-color: var(--state-climate-off-color, var(--state-inactive-color, #9e9e9e)); }
    header, section { padding: 16px 20px; }
    header { position: relative; min-height: 50px; display: flex; justify-content: center; align-items: center; box-sizing: border-box; }
    .title-block { min-width: 0; text-align: center; }
    .title-block p { text-transform: capitalize; }
    .more-info { position: absolute; right: 8px; inset-inline-end: 8px; border: 0; border-radius: var(--ha-border-radius-pill, 999px); color: var(--secondary-text-color); background: transparent; }
    h2, h3, p { margin: 0; }
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
    .control-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 16px; padding: 12px; border-radius: var(--ha-border-radius-lg, 12px); background: var(--secondary-background-color, color-mix(in srgb, var(--primary-text-color) 5%, var(--card-background-color))); }
    .field { display: grid; gap: 5px; }
    .target-chips { display: flex; gap: 6px; overflow-x: auto; padding: 0 20px 4px; scrollbar-width: thin; }
    .target-chips button { flex: 0 0 auto; text-transform: none; }
    .plan-row { padding: 0 20px 12px; }
    .plan-chip { position: relative; display: inline-block; }
    .chip { display: inline-flex; align-items: center; gap: 6px; text-transform: none; }
    .chip .auto-badge { padding: 1px 7px; border-radius: 999px; color: var(--text-primary-color, white); background: var(--feature-color); font-size: 10px; text-transform: uppercase; }
    .chip ha-icon { margin: 0; }
    .plan-menu { position: absolute; z-index: 5; left: 0; top: calc(100% + 4px); min-width: 180px; margin: 0; padding: 6px; list-style: none; border: 1px solid var(--divider-color); border-radius: var(--ha-border-radius-md, 8px); background: var(--card-background-color); box-shadow: 0 6px 20px rgba(0,0,0,.2); }
    .plan-menu li { display: block; }
    .plan-menu button { width: 100%; justify-content: flex-start; margin: 2px 0; border: 0; border-radius: 6px; text-align: left; text-transform: none; }
    .summary-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
    .summary-actions button { flex: 1 1 auto; justify-content: center; }
    .block-copy span { font-variant-numeric: tabular-nums; }
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
    .icon { width: 40px; padding: 7px; }
    .icon ha-icon { margin: 0; }
    .collapse-button { flex: 0 0 auto; border: 0; color: var(--secondary-text-color); background: transparent; }
    [hidden] { display: none !important; }
    .custom-time { display: flex; align-items: center; gap: 6px; margin-left: auto; }
    .custom-time input { width: 68px; }
    .timer-row { display: grid; gap: 12px; margin-top: 14px; }
    .timer-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .message { padding: 10px 20px; border-top: 1px solid var(--divider-color); color: var(--secondary-text-color); font-size: 13px; }
    .empty { padding: 28px 20px; color: var(--secondary-text-color); text-align: center; }
    ha-card.compact header { min-height: 44px; padding-block: 10px; }
    ha-card.compact .climate { padding: 4px 16px 12px; }
    ha-card.compact .modes { margin-top: 12px; }
    ha-card.compact .subsection-heading { margin-top: 12px; }
    ha-card.compact section:not(.climate) { padding: 12px 16px; }
    ha-card.compact .control-grid { margin-top: 10px; }
    ha-card.compact .feature-buttons button { min-height: 44px; }
    @media (max-width: 420px) {
      header, section { padding: 16px; }
      .control-grid { grid-template-columns: 1fr; }
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
let st = F;
customElements.get("scheduled-climate-card") || customElements.define("scheduled-climate-card", st);
window.customCards = window.customCards ?? [];
window.customCards.some((r) => r.type === "scheduled-climate-card") || window.customCards.push({
  type: "scheduled-climate-card",
  name: "Scheduled Climate Card",
  description: "Climate controls with weekly schedule plans, holds, and one-shot timers.",
  preview: !0
});
export {
  st as ScheduledClimateCard
};
