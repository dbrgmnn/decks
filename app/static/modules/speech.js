// Front-side pronunciation. The card text decides the voice language, so a
// deck can mix languages without a per-deck setting. Scripts with a unique
// alphabet are decisive; Latin-script languages are scored by characteristic
// letters and common function words.

const profile = (lang, chars, words, prefixes, suffixes, charScore = 5) => ({
  lang,
  chars,
  charScore,
  words: new Set(words.split(' ')),
  prefixes,
  suffixes,
});

// Distinctive alphabets first, then the generic script as a fallback.
const SCRIPT_LANGUAGES = [
  [/[іїєґ]/i, 'uk-UA'],
  [/[ў]/i, 'be-BY'],
  [/[ђјљњћџ]/i, 'sr-RS'],
  [/[ѓќѕ]/i, 'mk-MK'],
  [/[\u0400-\u04FF]/, 'ru-RU'],
  [/[\u0370-\u03FF]/, 'el-GR'],
  [/[\u0530-\u058F]/, 'hy-AM'],
  [/[\u10A0-\u10FF]/, 'ka-GE'],
  [/[\u0590-\u05FF]/, 'he-IL'],
  [/[پچژگکی]/, 'fa-IR'],
  [/[\u0600-\u06FF]/, 'ar-SA'],
  [/[\u0900-\u097F]/, 'hi-IN'],
  [/[\u0980-\u09FF]/, 'bn-BD'],
  [/[\u0B80-\u0BFF]/, 'ta-IN'],
  [/[\u0C00-\u0C7F]/, 'te-IN'],
  [/[\u0E00-\u0E7F]/, 'th-TH'],
  [/[\u3040-\u30FF]/, 'ja-JP'],
  [/[\uAC00-\uD7AF]/, 'ko-KR'],
  [/[\u4E00-\u9FFF]/, 'zh-CN'],
];

const LATIN_PROFILES = [
  profile(
    'de-DE',
    /[äöüß]/i,
    'der die das den dem des ein eine einen einem einer eines und oder aber nicht kein keine ist sind sein bin bist ich du er sie es wir ihr uns euch mein dein ihr unser euer mit für von zu zum zur auf im als auch noch nur sehr habe hast hatte hatten haben werden wird wurde kann können muss müssen dass wie wo wann warum welcher welche welches dieser diese dieses hier dort gestern heute morgen vorgestern übermorgen',
    /^(ge|ent|zer|vor|nach|über|unter|zusammen)/,
    /(ung|heit|keit|lich|isch|chen|lein|schaft|bar|sam|los|voll|frei|weise)$/,
    1,
  ),
  profile(
    'en-US',
    null,
    'the a an and or but not no is are was were am be been being have has had do does did will would can could should may might must shall to of in on at for with from by as that this these those it its he she they we you i me him her them us my your his their our who whom which what when where why how there here all any some more most other such only own same so than too very just',
    null,
    /(tion|sion|ness|ment|able|ible|ous|ful|less|ing|ed|ly|ship|hood|ward)$/,
  ),
  profile(
    'es-ES',
    /[ñ¿¡]/i,
    'el la los las un una unos unas y pero no de del al que en es son era eran ser estar soy eres somos estoy está están por para con sin su sus mi mis tu tus nuestro nuestra este esta estos estas ese esa eso esto hay muy más menos como cuando donde porque quien quienes todo toda todos todas también ya solo sí',
    null,
    /(ción|ciones|dad|tad|mente|oso|osa|ito|ita|illo|illa|ado|ida|ando|iendo)$/,
  ),
  profile(
    'fr-FR',
    /[çœæ]/i,
    'le la les un une des du de et ou mais non ne pas que qui quoi dont où quand comment pourquoi dans pour par avec sans sur sous chez au aux ce cette ces cet celui celle ceux celles il elle ils elles nous vous je tu on mon ma mes ton ta tes son sa ses notre nos votre vos leur leurs est sont était être avoir ai as a avons avez ont très plus moins aussi encore déjà toujours jamais tout tous toute toutes',
    null,
    /(tion|sion|ment|eux|euse|ique|able|ible|ance|ence)$/,
  ),
  profile(
    'it-IT',
    null,
    'il lo la i gli le un uno una di del della dei degli delle che e è ed ma non in con per su da al alla allo agli alle come più meno questo questa questi queste quello quella sono essere ho hai ha abbiamo avete hanno mio mia miei tuo tua suoi sua nostro nostra vostro vostra loro',
    null,
    /(zione|zioni|mente|issimo|issima|oso|osa|are|ere|ire|ato|ata|ito|ita|ando|endo)$/,
  ),
  profile(
    'pt-BR',
    /[ãõ]/i,
    'o a os as um uma uns umas de do da dos das que e ou mas não em no na nos nas por para com sem seu sua seus suas este esta estes estas esse essa isso isto como mais menos muito muita também já ainda ser estar é são foi era tem têm há ao aos à às pelo pela',
    null,
    /(ção|ções|mente|oso|osa|inho|inha|ado|ada|ido|ida|ando|endo)$/,
  ),
  profile(
    'nl-NL',
    /ij/,
    'de het een en van in is dat op te zijn met voor niet aan er maar om hem dan zou of wat mijn men dit zo door over ze zich bij ook tot je mij uit daar haar naar heb hoe heeft hebben deze want nog zal me zij nu geen omdat iets worden toch al waren veel meer doen toen moet ben zonder kan hun dus alles onder ja eens hier wie werd altijd doch wordt wezen kunnen ons',
    null,
    /(heid|lijk|baar|schap|tje|eren)$/,
    1,
  ),
  profile(
    'pl-PL',
    /[ąćęłńóśźż]/i,
    'i w na z do nie że się jest są to tego tej tym dla jak co ale od po za oraz być jestem jesteś jesteśmy',
    null,
    /(ować|owanie|anie|enie|owy|owa|owe|ach|ami)$/,
  ),
  profile(
    'cs-CZ',
    /[ěščřžůťďň]/i,
    'a v na se je že to ten ta ty do pro z za jako ale nebo není jsou byl byla bylo být jsem jsi jsme jste',
    null,
    /(ovat|ování|ový|ová|ové|ách|ami)$/,
  ),
  profile(
    'tr-TR',
    /[ğışİĞŞ]/,
    've bir bu şu o da de için ile değil var yok olan olarak ne nasıl neden çok daha en gibi ama',
    null,
    /(lar|ler|dan|den|ın|in|un|ün)$/,
  ),
  profile(
    'ro-RO',
    /[ăâîșț]/i,
    'și în de la cu pe un o este sunt nu că pentru din se mai ca',
    null,
    /(ție|ții|ul|ului|ilor|ele|elor)$/,
  ),
  profile(
    'hu-HU',
    /[őű]/i,
    'a az és hogy nem van vannak egy ez azt is meg de vagy már csak',
    null,
    /(ban|ben|nak|nek|val|vel|ként|ért|ból|ből|ról|ről|tól|től)$/,
  ),
  profile(
    'sv-SE',
    /[åäö]/i,
    'och att det en ett är jag du han hon vi ni de inte med för på som av till från har hade var',
    null,
    /(het|ningen|ning|arna|erna|ande|ende)$/,
    1,
  ),
  profile(
    'nb-NO',
    /[æøå]/i,
    'og er det en et jeg du han hun vi dere de ikke med for på som av til fra har hadde var',
    null,
    /(het|ingen|ning|ene|ende|else)$/,
    1,
  ),
  profile(
    'fi-FI',
    /[äö]/i,
    'ja on ei se että hän minä sinä olen olet ovat oli mutta kun niin kuin vain myös nyt',
    null,
    /(ssa|ssä|sta|stä|lla|llä|lle|ksi|tta|ttä)$/,
    1,
  ),
  profile(
    'vi-VN',
    /[\u1EA0-\u1EF9ăâđêôơư]/i,
    'và là của không có được trong một những cho với này đó',
    null,
    /(ng|nh|ch|tr|ph|th)$/,
  ),
  profile(
    'id-ID',
    null,
    'dan yang di ke dari untuk dengan tidak ini itu adalah saya kamu dia mereka kita akan pada juga ada bisa',
    null,
    /(kan|an|nya|ku|mu|lah|kah)$/,
  ),
];

const TOKEN = /\p{L}[\p{L}\p{M}'’-]*/gu;
const LATIN_UI_LANGUAGES = new Set([
  'af', 'ca', 'cs', 'cy', 'da', 'de', 'en', 'es', 'et', 'eu', 'fi', 'fr', 'ga',
  'gl', 'hr', 'hu', 'id', 'is', 'it', 'la', 'lt', 'lv', 'ms', 'mt', 'nl', 'no',
  'nb', 'pl', 'pt', 'ro', 'sk', 'sl', 'sq', 'sv', 'tl', 'tr', 'vi',
]);

let lastDetected = null;

const normalizeLang = lang => String(lang || '').toLowerCase().replace(/_/g, '-');

const detectLatin = text => {
  const lower = text.toLowerCase();
  const tokens = lower.match(TOKEN) || [];
  let best = null;

  for (const entry of LATIN_PROFILES) {
    let score = entry.chars && entry.chars.test(lower) ? entry.charScore : 0;
    for (const token of tokens) {
      if (entry.words.has(token)) score += 2;
      if (entry.prefixes && entry.prefixes.test(token)) score += 0.5;
      if (entry.suffixes && entry.suffixes.test(token)) score += 0.5;
    }
    if (score && (!best || score > best.score)) best = {lang: entry.lang, score};
  }

  // One weak clue (an affix or an umlaut) is not enough: short words are
  // genuinely ambiguous, so the session fallback handles them instead.
  return best && best.score >= 2 ? best.lang : null;
};

export const detectSpeechLanguage = text => {
  if (!text) return null;
  for (const [chars, lang] of SCRIPT_LANGUAGES) {
    if (chars.test(text)) return lang;
  }
  return detectLatin(text);
};

const fallbackSpeechLanguage = () => {
  const ui = normalizeLang(navigator.language) || 'en-US';
  return LATIN_UI_LANGUAGES.has(ui.split('-')[0]) ? ui : 'en-US';
};

// Remember the last confident match: a one-word card without any clue then
// uses the language of its deck or neighbours instead of the UI locale.
export const speechLanguageFor = (text, preferred = null) => {
  const detected = detectSpeechLanguage(text);
  if (detected) {
    lastDetected = detected;
    return detected;
  }
  return preferred || lastDetected || fallbackSpeechLanguage();
};

export const resetSpeechLanguage = () => {
  lastDetected = null;
};

const speechAvailable = () => (
  typeof window !== 'undefined'
  && 'speechSynthesis' in window
  && 'SpeechSynthesisUtterance' in window
);

const pickVoice = lang => {
  const target = normalizeLang(lang);
  const base = target.split('-')[0];
  const voices = speechSynthesis.getVoices();
  return voices.find(voice => normalizeLang(voice.lang) === target)
    || voices.find(voice => normalizeLang(voice.lang).split('-')[0] === base)
    || null;
};

export const canSpeak = speechAvailable;

export const stopSpeaking = () => {
  if (speechAvailable()) speechSynthesis.cancel();
};

export const speakText = (text, lang, onDone = null) => {
  if (!speechAvailable() || !text) return null;
  speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);
  const voice = pickVoice(lang);
  utterance.lang = voice ? voice.lang : lang;
  if (voice) utterance.voice = voice;
  if (onDone) {
    utterance.onend = onDone;
    utterance.onerror = onDone;
  }
  speechSynthesis.speak(utterance);
  return utterance;
};
