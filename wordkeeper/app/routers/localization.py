from fastapi import Request

def get_language(request: Request) -> str:
    """
    Určuje preferovaný jazyk používateľa na základe požiadavky.
    Priorita je nasledovná:
    1. Query parameter 'lang'.
    2. Cookie 'language' alebo 'lang'.
    3. Hlavička 'accept-language' (iba prvý jazyk v zozname).
    4. Predvolený jazyk 'en'.
    """
    # 1. Skontroluj query parameter
    lang = request.query_params.get("lang")
    if lang in ["en", "sk"]:
        return lang

    # 2. Skontroluj cookie
    cookie_lang = request.cookies.get("language") or request.cookies.get("lang")
    if cookie_lang in ["en", "sk"]:
        return cookie_lang

    # 3. Skontroluj 'accept-language' hlavičku (iba prvý jazyk)
    accept_language = request.headers.get("accept-language", "")
    if accept_language and "sk" in accept_language.lower().split(',')[0]:
        return "sk"

    # 4. Predvolený jazyk
    return "en"