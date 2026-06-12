ahoj skontroluj moj kod
https://github.com/Lipnicanmilos/wordkeeper
PWA mozes mi ked som online ulozit vsetky categorie a slovicka do pamati
aby som offline mohol pracovat so vsetkym profil, vsetky kategorie aj tie nekliknute v online rezime
aj vsetky testy a repeaty a slovicka?


Hlavné problémy
1. test.html — žiadny offline fallback
/api/v1/words/test/start je POST — SW ho úplne ignoruje (riadok v sw.js: if (event.request.method !== 'GET') return). Keď si offline, test sa nespustí a kód ani nemá catch s fallbackom.
2. /api/v1/words/test/submit (POST) sa offline stratí
Výsledky testu sa neukložia do žiadnej fronty. Po reconnecte sa knowledge level neaktualizuje.
3. prefetchAllWords čaká na serviceWorker.controller
Pri prvom načítaní stránky (hneď po inštalácii SW) je controller ešte null — prefetch sa preskoči úplne, aj keď je fallback kód v prefetchAllWords napísaný.
4. repeat.html — offline cache funguje len pre kombináciu (categoryId + level + direction) ktorú si už raz otvoril online. Nové levely alebo kategórie bez predchádzajúcej návštevy nemajú cache.
5. Štatistiky (/api/user/stats) sa nekešujú do localStorage na profile.html — vidno len na dashboarde.

🛠 Prioritne opravy (už schválené)
✅ 1) test.html — offline fallback cez localStorage (start cache)
✅ 2) test.html — offline queue pre submit (POST) v localStorage + flush pri online reconnectu
⬜ 3) sw.js / prefetchAllWords race (controller null)
⬜ 4) repeat.html offline cache rozšíriť pre nové kombinácie bez predchádzajúcej návštevy
⬜ 5) profile.html — ukladať /api/user/stats do localStorage online, čítať offline

🔝 Navrhovaná priorita (poradie prác)
⬜ A) SECRET_KEY hard-fail v produkcii (rýchle + bezpečnostné)
⬜ B) sw.js / prefetchAllWords race (controller null) (základ pre spoľahlivý prefetch po inštalácii)
⬜ C) repeat.html — offline cache rozšíriť aj pre nové kombinácie (aby offline fungovalo “naozaj všetko”)
⬜ D) profile.html — stats do localStorage online + čítanie offline (UX)
⬜ E) Refaktor main.py (údržba, väčšia práca)
⬜ F) Freemium/monetizácia (produktová vec, keď je offline-first stabilné)



1. 💳 Platená vs. bezplatná vrstva (Freemium)

Bez toho nebudeš mať ako zarábať.

    Obmedz bezplatnú verziu: Napr. max 50 vlastných slovíčok, žiadne pokročilé štatistiky, bez synchronizácie medzi zariadeniami (to je silná funkcia na predaj).

    Čo dať do plateného tieru (napr. 2-5 €/mesiac alebo 20€ doživotne):

        Neobmedzený počet slovíčok

        Synchronizácia cez Supabase (viac zariadení)

        Export/import svojich setov (CSV, Anki formát)

        Pokročilé štatistiky (krivka zabúdania, odhady kedy si čo zopakovať)

        Tematické balíčky slovíčok (napr. obchodná angličtina)

2. 🧾 Systém správu používateľov a platieb

    Registrácia / Prihlásenie: To už asi máš (podľa JWT v requirements.txt). Doplň social login (Google, Apple) – zvyšuje konverziu.

    Platobná brána: Stripe (najjednoduchšie na integráciu, podporuje jednorazové aj opakované platby). Alebo Lemon Squeezy – lepšie pre digital products a daňové povinnosti.

    Webhooky: Stripe → tvoj backend → aktualizácia user.plan v Supabase.

3. 📊 Administračné rozhranie

Bez neho nevieš, kto platí a riešiť problémy.

    Jednoduchý admin dashboard (môže byť len pre teba, nemusí byť pekný):

        Zoznam používateľov + ich plán

        Zrušenie predplatného

        Manuálne predĺženie licencie

        (Neskôr) základné metriky – DAU, počet vytvorených balíčkov

4. 🧪 Bezproblémové skúšanie (trial)

Nikto nechce platiť za niečo, čo nevyskúša.

    Pridaj 14-dňový trial na plnú verziu – bez zadania karty (tzv. "no-commitment trial"). Stačí email.

    Po trialoch – obmedzená free verzia.

    Nezabudni na pripomienky pred koncom trialu (email / notifikácia v appke).

5. 🏷️ Profesionálny imidž a dôvera

Komerčná appka musí vyzerať a správať sa dôveryhodne.

    Pridať README.md (ako som písal minule) – nie pre komerčnosť priamo, ale keď ťa niekto nájde, je to vizitka.

    Obrazovka s cenami – jasná, jednoduchá, s vysvetlením čo obsahuje free vs. paid.

    GDPR / Ochrana súkromia – ak zbieraš email a slovíčka, musíš mať:

        Súhlas s cookies / spracovaním údajov

        Možnosť vymazať účet aj s dátami

        (Stripe to rieši za teba, ale tvoja appka to musí rešpektovať)

6. 🧠 Čo ťa odlíši od Anki, Quizlet atď.?

Komerčne uspeješ, ak ponúkneš niečo, čo oni nemajú (dobre alebo jednoduchšie).

    Offline first + synchronizácia – to už máš rozrobené v TODO.md. Je to tvoja zbraň. Veľa ľudí nemá stále internet (metro, lietadlo, dedina).

    Veľmi jednoduché vytváranie – možno AI helper: "Nahraj text a appka sama navrhne slovíčka na učenie".

    Gamifikácia – denné streak, levelovanie, porovnávanie s ostatnými (nepodceňuj – funguje to).

⚠️ Jedno veľké "pozor"

Tvoja appka je teraz open-source na GitHube. Ak ju začneš predávať, niekto si môže spraviť vlastnú kópiu zadarmo.

    Riešenie: Repozitár ponechaj ako ukážku, ale kľúčové časti (platobný modul, synchro backend, admin) nedávaj verejne. Alebo zmeň licenciu na niečo ako "source available but not for commercial use".

✅ Čo by som spravil ako prvý krok (aby si otestoval komerčný záujem bez veľkej námahy):

    Pridám do appky tlačidlo "Podporiť projekt" (Buy me a coffee / GitHub Sponsors).

    Ak niekto zaplatí, ručne mu pošlem licenčný kľúč a odomknem funkcie. (Áno, je to manuálne, ale za 1 večer spravíš MVP monetizácie.)

    Uvidíš, či vôbec niekto chce platiť. Ak áno, vtedy spravíš Stripe integráciu.


----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Super ✅ Aktuálny stav appky:
OblasťStavOffline/PWA✅N+1 queries✅Security (ownership checks)✅Vyčistené mŕtve súbory✅README✅Rate limiting (login/register/reset)✅
Zostáva z nášho zoznamu:

SECRET_KEY hard-fail v produkcii (1 riadok, rýchle)
Refaktorizácia main.py (väčšia práca)
Freemium/monetizácia
