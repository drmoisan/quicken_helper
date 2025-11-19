# quicken_helper/qfx_to_txns.py
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, cast


def _to_date(s: str) -> str:
    # ofx dates often like 20250115 or 20250115T120000
    if not s:
        return ""
    s = s.strip()
    # strip timezone offsets like "[0:GMT]"
    s = s.split("[", 1)[0]
    # pick YYYYMMDD part
    digits = "".join(ch for ch in s if ch.isdigit())
    if len(digits) >= 8:
        y, m, d = digits[:4], digits[4:6], digits[6:8]
        try:
            return datetime(int(y), int(m), int(d)).strftime("%m/%d/%Y")
        except Exception:
            pass
    return ""


def _tx(
    amount: float, payee: str = "", memo: str = "", date: str = "", checknum: str = ""
) -> dict[str, Any]:
    # conform to your existing schema used in qif_to_csv paths
    return {
        "date": date,  # "mm/dd/YYYY"
        "payee": payee or "",
        "amount": f"{amount:.2f}",
        "category": "",
        "memo": memo or "",
        "account": "",
        "checknum": checknum or "",
        "splits": [],
    }


def parse_qfx(path: Path | str) -> list[dict[str, Any]]:
    """
    Parse a QFX/OFX file into the same txns dict schema as parse_qif().
    Prefers ofxparse if installed; falls back to a light SGML parser.
    """
    p = Path(path)
    raw = p.read_text(encoding="utf-8", errors="ignore")

    # --- try ofxparse first ---
    try:
        import ofxparse  # type: ignore

        parser_cls = cast("Any", getattr(ofxparse, "OfxParser", None))
        if parser_cls is None:
            raise ImportError("ofxparse.OfxParser is unavailable")
        with p.open("rb") as f:
            ofx_root: Any = parser_cls.parse(f)
        out: list[dict[str, Any]] = []
        accounts = cast("Sequence[Any] | None", getattr(ofx_root, "accounts", None))
        if accounts:
            for acct in accounts:
                statement = getattr(acct, "statement", None)
                transactions = (
                    getattr(statement, "transactions", None)
                    if statement is not None
                    else None
                )
                if not transactions:
                    continue
                for tr in transactions:
                    amount_val = getattr(tr, "amount", 0.0) or 0.0
                    amt = float(amount_val)
                    payee_raw = getattr(tr, "payee", "") or ""
                    memo_raw = getattr(tr, "memo", "") or ""
                    payee = (payee_raw or memo_raw).strip()
                    memo = memo_raw.strip()
                    date_obj = getattr(tr, "date", None)
                    formatted_date = (
                        _to_date(date_obj.strftime("%Y%m%d"))
                        if date_obj is not None
                        else ""
                    )
                    checknum_val = getattr(tr, "checknum", "") or ""
                    checknum = str(checknum_val)
                    out.append(_tx(amt, payee, memo, formatted_date, checknum))
        return out
    except Exception:
        pass  # fall through to minimal fallback

    # --- minimal fallback (SGML-ish tag scanning) ---
    # We’ll scan for <STMTTRN> blocks and pick child tags we care about.
    # This won’t cover every OFX variant, but handles common QFX exports.
    lower = raw.lower()
    out: list[dict[str, Any]] = []
    start = 0
    while True:
        i = lower.find("<stmttrn>", start)
        if i == -1:
            break
        j = lower.find("</stmttrn>", i)
        if j == -1:
            break
        block = raw[i:j]

        def tagval(tag: str, text_block: str) -> str:
            # <TAG>value on same line OR <TAG>value</TAG>
            # do a simple search ignoring case
            t = tag.lower()
            k = text_block.lower().find(f"<{t}>")
            if k == -1:
                return ""
            k2 = k + len(t) + 2
            # read to end of line or next angle bracket
            end = text_block.find("<", k2)
            val = text_block[k2:end] if end != -1 else text_block[k2:]
            return val.strip()

        amount_s = tagval("TRNAMT", block)
        name = tagval("NAME", block)
        memo = tagval("MEMO", block)
        dtposted = tagval("DTPOSTED", block)
        checknum = tagval("CHECKNUM", block)

        try:
            amt = float(amount_s.replace(",", ""))
        except Exception:
            amt = 0.0
        out.append(
            _tx(
                amt,
                payee=name or memo,
                memo=memo,
                date=_to_date(dtposted),
                checknum=checknum,
            )
        )
        start = j + len("</stmttrn>")
    return out
