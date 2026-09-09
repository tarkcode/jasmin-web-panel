/* ============================================================
 * SMS segment / encoding calculator  (window.SmsSegments)
 * ------------------------------------------------------------
 * Detects GSM-7 vs UCS-2 (Unicode) encoding and computes the
 * real number of SMS segments the message will bill as.
 *   GSM-7 : 160 chars single / 153 per part when multipart
 *   UCS-2 : 70  chars single / 67  per part when multipart
 * A single non-GSM character (emoji, smart quote, ş/ğ/İ/ı, …)
 * forces the WHOLE message to UCS-2 -> ~70 chars per segment.
 * Reusable anywhere: SmsSegments.analyze(text) / .normalize(text)
 * ============================================================ */
(function (global) {
    // GSM 03.38 basic set — each character is one septet (LF/CR/space included).
    var BASIC = "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà";
    // GSM 03.38 extension set — each of these costs TWO septets (ESC + char).
    var EXT = "\f^{}\\[~]|€";
    var basicSet = new Set(Array.from(BASIC));
    var extSet = new Set(Array.from(EXT));

    // Common Unicode look-alikes -> GSM-safe equivalents.
    var NORMALIZE = {
        "‘": "'", "’": "'", "‚": "'", "′": "'", "`": "'",
        "“": '"', "”": '"', "„": '"', "″": '"',
        "–": "-", "—": "-", "―": "-", "−": "-", "‐": "-", "‑": "-",
        "…": "...",
        " ": " ", " ": " ", " ": " ", " ": " ", " ": " ",
        "•": "-", "·": ".",
        // Turkish letters that are NOT in GSM-7 (İ ı Ş ş Ğ ğ ç):
        "İ": "I", "ı": "i", "Ş": "S", "ş": "s",
        "Ğ": "G", "ğ": "g", "ç": "c"
    };

    // analyze(text[, force]) — force is optional: "ucs2" or "gsm" to compute for
    // a specific encoding (e.g. a UI that lets the user pick). Omit for real
    // auto-detection (a single non-GSM char -> UCS-2).
    function analyze(text, force) {
        text = text || "";
        var cps = Array.from(text);           // iterate by code point
        var naturallyGsm = true, nonGsm = [];
        for (var i = 0; i < cps.length; i++) {
            var c = cps[i];
            if (basicSet.has(c) || extSet.has(c)) continue;
            naturallyGsm = false;
            if (nonGsm.indexOf(c) === -1) nonGsm.push(c);
        }
        var isGsm;
        if (force === "gsm" || force === "GSM-7") isGsm = true;
        else if (force === "ucs2" || force === "UCS-2") isGsm = false;
        else isGsm = naturallyGsm;

        var singleLimit, multiLimit, units;
        if (isGsm) {
            singleLimit = 160; multiLimit = 153;
            units = cps.map(function (c) { return extSet.has(c) ? 2 : 1; });
        } else {
            singleLimit = 70; multiLimit = 67;
            // UCS-2: characters above the BMP (emoji) take two UTF-16 code units.
            units = cps.map(function (c) { return c.codePointAt(0) > 0xFFFF ? 2 : 1; });
        }

        var total = units.reduce(function (a, b) { return a + b; }, 0);
        var segments;
        if (total === 0) {
            segments = 0;
        } else if (total <= singleLimit) {
            segments = 1;
        } else {
            // Pack per part so no character straddles a segment boundary.
            segments = 1;
            var cur = 0;
            for (var j = 0; j < units.length; j++) {
                if (cur + units[j] > multiLimit) { segments++; cur = 0; }
                cur += units[j];
            }
        }
        var perSegment = segments <= 1 ? singleLimit : multiLimit;
        var capacity = segments * perSegment;

        return {
            encoding: isGsm ? "GSM-7" : "UCS-2",
            isGsm: isGsm,
            naturallyGsm: naturallyGsm, // true only if NO non-GSM chars present
            chars: cps.length,          // human-visible characters
            encodedLength: total,       // billed units (septets or code units)
            segments: segments,
            perSegment: perSegment,
            remaining: segments === 0 ? singleLimit : (capacity - total),
            singleLimit: singleLimit,
            multiLimit: multiLimit,
            nonGsm: nonGsm              // the characters forcing UCS-2
        };
    }

    // Replace look-alike Unicode with GSM equivalents; strip anything that
    // genuinely can't be represented (emoji, CJK…). Returns {text, replaced, stripped}.
    function normalize(text) {
        text = text || "";
        var cps = Array.from(text), out = "", replaced = 0, stripped = 0;
        for (var i = 0; i < cps.length; i++) {
            var c = cps[i];
            if (Object.prototype.hasOwnProperty.call(NORMALIZE, c)) { out += NORMALIZE[c]; replaced++; continue; }
            if (basicSet.has(c) || extSet.has(c)) { out += c; continue; }
            stripped++; // unmappable non-GSM char -> drop
        }
        return { text: out, replaced: replaced, stripped: stripped };
    }

    global.SmsSegments = { analyze: analyze, normalize: normalize };
})(window);
