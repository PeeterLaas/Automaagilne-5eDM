# 🎲 Kiirjuhend: AI-koopameister Pi agendiga

See juhend aitab sul mängida D&D-d nii, et koopameistri (Dungeon Master, DM) rolli täidab
tehisintellekti agent [Pi](https://pi.dev). Kõik vajalik on tasuta. Krediitkaarti pole vaja.

**Kuidas see töötab?** Agent loeb failist `play/AGENTS.md` juhised, kuidas olla koopameister. Täringuid
veeretab ta Pythoni skriptidega (`scripts/roll.py` jt), mitte ei mõtle numbreid välja. Mängu seis
salvestatakse kausta `play/campaigns/`, nii et lugu jätkub ka järgmisel korral.

---

## 1. Paigalda vajalik tarkvara

| Mida | Milleks | Kontrolli käsuga |
|---|---|---|
| [Python 3.10+](https://www.python.org/downloads/) | täringud, võitlus, salvestused | `python3 --version` |
| [Node.js 22+](https://nodejs.org) | Pi agendi jaoks | `node --version` |
| [Git](https://git-scm.com) | repositooriumi allalaadimiseks | `git --version` |

Seejärel paigalda Pi:

```bash
curl -fsSL https://pi.dev/install.sh | sh
```

Windowsis kasuta PowerShellis käsku `irm https://pi.dev/install.ps1 | iex`. Windowsis kirjuta ka
`python3` asemel `python`.

## 2. Hangi tasuta API-võti (OpenRouter)

1. Loo konto aadressil <https://openrouter.ai>.
2. Ava **Settings → API Keys** ja vajuta **Create key**. Kopeeri võti (algab `sk-or-`).
3. Anna võti Pi-le. Lihtsaim viis on käivitada `pi` ja kirjutada seal `/login`.
   Teine võimalus on panna võti terminalis keskkonnamuutujasse:
   ```bash
   export OPENROUTER_API_KEY=sk-or-...
   ```

⚠️ **API-võti on salajane nagu parool.** Ära jaga seda kellegagi ega lisa seda gitti.

## 3. Lae mäng alla ja alusta

```bash
git clone <kursuse repositooriumi aadress>
cd <repositooriumi kaust>/play
pi --model "openrouter/nvidia/nemotron-3-super-120b-a12b:free" --models "openrouter/*:free"
```

Esimesel käivitamisel küsib Pi, kas usaldad selle kausta seadistusi (*trust project*). Vasta
**jah**, muidu ei laadi mängukäsud.

Nüüd kirjuta lihtsalt eesti keeles, näiteks *„Alustame uut seiklust!"*. Koopameister vastab samas
keeles, milles sina kirjutad.

### Kasulikud käsud Pi sees

| Käsk | Mida teeb |
|---|---|
| `/play` | jätkab pooleli jäänud mängu või alustab uut |
| `/new-campaign Uppunud kroon` | loob uue kampaania ja alustab tegelase loomist |
| `/save` | salvestab mängu seisu (tee seda enne lõpetamist!) |
| `/recap` | tuletab meelde, mis seni juhtunud on |
| `/model` | vali teine keelemudel |
| **Ctrl+P** | vaheta järgmisele tasuta mudelile |

### Kuidas mängida

- Kirjelda, mida su tegelane teeb: *„Püüan valvurit ära rääkida, et ta meid läbi laseks."*
- Kui tegevusel on risk, ütleb koopameister, mida veeretada. Näiteks: *„Veereta d20 + Veenmine (+3),
  raskusaste 15."* Võid veeretada päris täringuid ja öelda tulemuse või paluda, et DM veeretaks.
- Vaenlaste ja NPC-de eest veeretab DM ise ning näitab arvutust.
- Kui DM unustab reegli, tuleta talle meelde: *„Veereta selle jaoks."* või *„Salvesta mäng."*

---

## Mida teada tasuta mudelitest

- **Päevas on 50 päringut.** Iga tööriista kasutus (täringuveeretus, faili lugemine) on eraldi
  päring. Ühe mängukäigu peale kulub tavaliselt 1–3 päringut, võitluses rohkem. Arvesta umbes
  15–25 käiguga päevas.
- **Tõrge `429 ... rate-limited`** tähendab, et see mudel on hetkel ülekoormatud. Vajuta **Ctrl+P**,
  et minna üle teisele tasuta mudelile, ja mängi edasi. Midagi ei kao, sest lugu on failides.
- **Tasuta mudelite valik muutub sageli.** Vaata hetkel saadaolevaid mudeleid käsuga
  `pi --list-models ":free"`.
- Suuremad mudelid jutustavad paremini ja peavad reeglitest paremini kinni.

## Edasijõudnutele: kohalik mudel Ollamaga

Kui arvutis on vähemalt 16 GB mälu, saad mängida ka ilma internetita ja ilma piiranguteta:

```bash
ollama pull qwen3:8b
OLLAMA_CONTEXT_LENGTH=16384 ollama serve
```

Seejärel kopeeri fail `docs/pi-models.ollama.json` asukohta `~/.pi/agent/models.json` ja käivita:

```bash
cd play
pi --model "ollama/qwen3:8b"
```

Väikesed kohalikud mudelid unustavad reegleid sagedamini kui suured pilvemudelid. Hea katse ongi
võrrelda, kuidas erineva suurusega mudelid samade juhistega toime tulevad.

## Ülesandeideid

1. **Muuda koopameistri isikupära.** Ava `play/AGENTS.md` ja kirjuta jutustamisstiil ümber, näiteks
   sarkastiliseks, õudusjutu stiilis või lastele sobivaks. Mängi sama stseen läbi enne ja pärast.
2. **Võrdle mudeleid.** Mängi sama algust kahe erineva mudeliga. Kumb veeretas täringuid õigel
   ajal? Kumb unustas salvestada? Kumb jutustas paremini?
3. **Lisa uus tööriist.** Kirjuta Pythoni skript (näiteks juhuslik ilmastik või kõrtsi nimede
   generaator) ja lisa selle kasutusjuhend faili `AGENTS.md`. Kas agent hakkab seda kasutama?

Täpsem ingliskeelne juhend, mis katab ka Claude Code'i ja Gemini CLI, on failis
[`PLAYING.md`](PLAYING.md).
