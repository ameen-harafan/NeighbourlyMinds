# Student 3 — Iteration 1 Threshold Evidence

## Scope

This note supports **AC 2.1.1: Dynamic 2D Contrast Slider Adjuster**.

The corrected DS allocation requires Student 3 to:
- choose and document the digital contrast measure;
- find an authoritative calculation method;
- check whether the proposed 30% threshold has a reliable source;
- explain screen RGB contrast versus physical material LRV;
- create test colour combinations and expected results;
- test boundary values;
- define clear badge labels; and
- avoid the word **"Safe"** unless an appropriate standard has been verified.

## 1. Digital method selected for Iteration 1

For the browser prototype, use the **W3C/WCAG sRGB relative luminance and contrast-ratio method**.

Contrast ratio:

`(L_lighter + 0.05) / (L_darker + 0.05)`

Relative luminance for sRGB:

`L = 0.2126R + 0.7152G + 0.0722B`

where R, G and B are first converted from 8-bit sRGB values to linear-light values.

For WCAG 2.2 Success Criterion 1.4.11, meaningful non-text user-interface components and graphical objects require a contrast ratio of at least **3:1** against adjacent colours.

**Prototype feedback rule:**
- `< 3:1` → **Low contrast**
- `>= 3:1` → **Improved contrast**

This rule is used as a **digital conceptual feedback boundary**, not as a real-world building compliance certificate.

## 2. What the 30% figure means

The project's backlog refers to a "safe 30% contrast guideline."

A 30% physical luminance-contrast requirement does have an Australian accessibility basis for doorway elements. The Association of Consultants in Access Australia summarises AS 1428.1:2021 Clause 10.1 as requiring a minimum 30% luminance contrast between specified doorway/surround combinations.

However, this is based on **physical luminance / Light Reflectance Values (LRVs)** of building surfaces.

It is not equivalent to a contrast ratio calculated from browser RGB/HEX values.

## 3. Decision for Iteration 1

**Do not convert RGB values into a claimed physical LRV percentage.**

The slider should be presented as a **conceptual digital contrast demonstration**.

Recommended wording:

> "This prototype demonstrates digital colour contrast. It does not measure the actual Light Reflectance Value (LRV) of paint or physical materials."

Recommended badges:

- **Low contrast**
- **Improved contrast**

Avoid:
- Safe
- Unsafe
- LRV compliant
- Meets 30% physical requirement

unless future iterations use verified real-world LRV measurements and the team has confirmed the applicable standard and method.

## References

1. W3C. *Web Content Accessibility Guidelines (WCAG) 2.2*, Success Criterion 1.4.11 Non-text Contrast.  
   https://www.w3.org/TR/WCAG22/#non-text-contrast

2. W3C. *Understanding Success Criterion 1.4.3: Contrast (Minimum)* — relative luminance definition and sRGB calculation.  
   https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum

3. Association of Consultants in Access Australia. *Access Insight June 2026: Luminance Contrast* — summary of AS 1428.1:2021 doorway luminance-contrast requirements.  
   https://access.asn.au/access-insight-june-2026-luminance-contrast/

## Evidence limitation

The Australian Standard itself is a controlled/copyrighted standards document. The project should verify exact compliance wording against an authorised copy of **AS 1428.1:2021** if the final product intends to make a formal standards-compliance claim.
