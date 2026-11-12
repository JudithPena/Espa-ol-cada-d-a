# Тема 24 «El español y yo — испанский и я» · A2 — карта экранов

Цели темы: рассказать, как давно и зачем вы учите испанский; сказать, что вы умеете, что знаете и что вам трудно; заполнить анкету и продиктовать фамилию по буквам; записаться в языковую школу и поговорить на языковом обмене.

Карта собрана из сценария уроков (`node tools/site_map_gen.cjs --unit 24 --write`): для A2 порядок шагов
проектируется в `docs/a2_c2_curriculum_map.md` (первая тема — в `docs/a2_pilot_blueprint.md`), карта фиксирует результат.
Обозначения — `docs/site_slide_maps/README.md`.

## Урок `espanol_y_yo/intercambio` — «Языковой обмен»

- **Цель:** понять на слух разговор о том, кто как давно и зачем учит язык.
- **Длина:** 19 шагов, около 7 минут. **Новая лексика:** desde, desde hace, ¿Cuánto tiempo hace que...?, el idioma, necesitar, la pronunciación, rápido.
- **Интерактив:** выбор 8, ввод 1, группы 1; на слух и с голосом собеседника — 2. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 1 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | T: text + dialogue | Мадрид, вечер языкового обмена. Ирина пришла впервые и знакомится с Диего. Послушайте раз… | — |
| 2 | C: выбор | ¿De dónde es Irina? → De Leópolis. | `intercambio` |
| 3 | C: выбор | ¿Qué idioma estudia Diego? → Inglés. | `intercambio` |
| 4 | W | новое слово: desde — с (какого-то момента) | — |
| 5 | W | новое слово: desde hace — уже (столько-то времени) | — |
| 6 | W | новое слово: ¿Cuánto tiempo hace que...? — как давно...? | — |
| 7 | W | новое слово: el idioma — язык (на котором говорят) | — |
| 8 | T: text + examples | В разговоре прозвучали два способа сказать, как давно что-то продолжается. Сравните их. | — |
| 9 | C: выбор | ¿Desde cuándo vive Irina en Madrid? → Desde enero. | `intercambio` |
| 10 | C: выбор | ¿Cuánto tiempo hace que Diego estudia inglés? → Dos años. | `intercambio` |
| 11 | C~: выбор на слух | на слух «Estudio inglés desde hace dos años.» → Я учу английский уже два года. | — |
| 12 | W | новое слово: necesitar — нуждаться; быть нужным | — |
| 13 | W | новое слово: la pronunciación — произношение | — |
| 14 | W | новое слово: rápido — быстро | — |
| 15 | C: выбор | ¿Para qué necesita Diego el inglés? → Para su trabajo. | `intercambio` |
| 16 | C: выбор | ¿Qué es difícil para Irina? → Entender a la gente cuando habla rápido. | `intercambio` |
| 17 | I~: диктант | на слух «Hace un año que estudio español.» → Hace un año que estudio español | — |
| 18 | S: группы | Кто это сказал?: Irina / Diego | `intercambio` |
| 19 | C: выбор | Вы согласны. → ¡Vale! ¡Perfecto! | — |

Сигнатура: `T(text+dialogue) C@intercambio×2 W×4 T(text+examples) C@intercambio×2 C~ W×3 C@intercambio×2 I~ S C`

## Урок `espanol_y_yo/desde_hace` — «Desde, desde hace, hace… que»

- **Цель:** сказать, с какого времени и как долго вы что-то делаете.
- **Длина:** 20 шагов, около 10 минут. **Новая лексика:** el verbo.
- **Интерактив:** выбор 5, ввод 8, сборка 2, группы 1, письмо 1; на слух и с голосом собеседника — 1. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 11 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | T: compare | С какого момента и как долго | — |
| 2 | W | новое слово: el verbo — глагол | — |
| 3 | C: выбор | Hace un año que estudio español. Какое слово здесь — el ver… → estudio | — |
| 4 | S: группы | Момент или срок?: desde… (момент) / desde hace… (срок) | — |
| 5 | I: ввод | Vivo en Valencia ___ tres años. → desde hace | — |
| 6 | I: ввод | Trabajo aquí ___ septiembre. → desde | — |
| 7 | I: ввод | Estudiamos español ___ seis meses. → desde hace | — |
| 8 | I: ввод | Carlos está en casa ___ las siete. → desde | — |
| 9 | T: compare | Как спросить | — |
| 10 | C: выбор | Вы живёте здесь два года. → Hace dos años. | — |
| 11 | C~: выбор на слух | на слух «Vivo aquí desde hace tres meses.» → Я живу здесь уже три месяца. | — |
| 12 | B: сборка | Hace seis meses que estudio español. | — |
| 13 | B: сборка | ¿Desde cuándo vives aquí? | — |
| 14 | I: ввод | Estudio inglés desde hace dos años. → Hace dos años que estudio inglés | — |
| 15 | I: ввод | Trabajo en un hospital desde hace un mes. → Hace un mes que trabajo en un hospital | — |
| 16 | I: ввод | Vivo en Madrid desde hace enero. → Vivo en Madrid desde enero | — |
| 17 | I: ввод | Estudio español desde un año. → Estudio español desde hace un año | — |
| 18 | O: письмо по признакам | ¿Cuánto tiempo hace que estudias español? Ответьте о себе о…; образец: Hace un año que estudio español. | — |
| 19 | Q: тест | Vivo aquí ___ 2020. → desde | — |
| 20 | Q: тест | ___ dos años que estudio español. → Hace | — |

Сигнатура: `T(compare) W C S I×4 T(compare) C C~ B×2 I×4 O Q×2`

## Урок `espanol_y_yo/para_que` — «¿Por qué? ¿Para qué?»

- **Цель:** объяснить, почему и для чего вы учите испанский.
- **Длина:** 18 шагов, около 8 минут. **Новая лексика:** ¿Para qué?, la cultura, el futuro, mejorar.
- **Интерактив:** выбор 4, ввод 5, сборка 2, группы 1, письмо 1; на слух и с голосом собеседника — 2. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 8 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | T: text + examples + compare | Ирина назвала сразу и причину, и цель. Чем отличаются эти два ответа? | — |
| 2 | W | новое слово: ¿Para qué? — для чего? зачем? | — |
| 3 | W | новое слово: la cultura — культура | — |
| 4 | W | новое слово: el futuro — будущее | — |
| 5 | W | новое слово: mejorar — улучшать; становиться лучше | — |
| 6 | S: группы | Причина или цель?: porque… / para… | — |
| 7 | I: ввод | Estudio español ___ quiero vivir en Sevilla. → porque | — |
| 8 | I: ввод | Estudio español ___ entender a mis amigos. → para | — |
| 9 | I: ввод | Estudio español ___ me encanta el idioma. → porque | — |
| 10 | I: ввод | Estudio español ___ mejorar mi futuro. → para | — |
| 11 | I: ввод | Estudio español para viajo por España. → Estudio español para viajar por España | — |
| 12 | C~: выбор на слух | на слух «Estudio español para trabajar en México.» → Чтобы работать в Мексике. | — |
| 13 | C~: выбор на слух | на слух «Estudio inglés porque lo necesito en el…» → Потому что он нужен мне на работе. | — |
| 14 | B: сборка | ¿Para qué estudias español? | — |
| 15 | B: сборка | Estudio español porque me encanta la cultura. | — |
| 16 | O: письмо по признакам | ¿Por qué o para qué estudias español? Напишите одну-две фра…; образец: Estudio español para viajar por España … | — |
| 17 | Q: тест | Estudio español ___ hablar con mi familia. → para | — |
| 18 | Q: тест | — ¿Por qué estudias inglés? — ___ lo necesito en el trabajo. → Porque | — |

Сигнатура: `T(text+examples+compare) W×4 S I×5 C~×2 B×2 O Q×2`

## Урок `espanol_y_yo/saber_conocer` — «Saber y conocer: два «знать»»

- **Цель:** сказать, что вы умеете, что знаете и с чем знакомы.
- **Длина:** 24 шага, около 11 минут. **Новая лексика:** saber, No sé., tocar, conducir.
- **Интерактив:** выбор 7, ввод 5, сборка 3, группы 1, письмо 1; на слух и с голосом собеседника — 1. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 9 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | T: text + dialogue | Ирина и Диего идут гулять. В их разговоре два разных глагола переводятся как «знать». Как… | — |
| 2 | W | новое слово: saber — знать; уметь | — |
| 3 | W | новое слово: No sé. — не знаю. | — |
| 4 | W | новое слово: tocar — играть (на инструменте); трогать | — |
| 5 | W | новое слово: conducir — водить машину | — |
| 6 | C: выбор | ¿Irina sabe dónde está el mercado? → No, no sabe. | `mercado` |
| 7 | C: выбор | ¿Qué sabe hacer Irina? → Cocinar comida ucraniana. | `mercado` |
| 8 | T: compare + conjugation + more | Saber или conocer? | — |
| 9 | S: группы | Saber или conocer?: saber / conocer | — |
| 10 | I: ввод | (yo) No ___ dónde están mis llaves. → sé | — |
| 11 | I: ввод | ¿(tú) ___ a mi amigo Carlos? → conoces | — |
| 12 | I: ввод | (yo) ___ Barcelona muy bien. → conozco | — |
| 13 | I: ввод | Mis padres no ___ hablar inglés. → saben | — |
| 14 | I: ввод | ¿(vosotros) ___ cocinar? → sabéis | — |
| 15 | T: compare | Не умею или не могу? | — |
| 16 | C: выбор | Вы умеете плавать, но сегодня болит нога. → Sé nadar, pero hoy no puedo. | — |
| 17 | C: выбор | Вы не знаете. → No, no sé. Lo siento. | — |
| 18 | C~: выбор на слух | на слух «¿Conoces a mi hermana?» → Ты знаком с моей сестрой? | — |
| 19 | B: сборка | ¿Sabes tocar la guitarra? | — |
| 20 | B: сборка | No conozco a tu hermana. | — |
| 21 | B: сборка | No sé conducir. | — |
| 22 | O: письмо по признакам | ¿Qué sabes hacer? Напишите, что вы умеете и чего не умеете.; образец: Sé cocinar y nadar, pero no sé tocar la… | — |
| 23 | Q: тест | — ¿___ a Lucía? — Sí, es mi amiga. → Conoces | — |
| 24 | Q: тест | No ___ conducir. → sé | — |

Сигнатура: `T(text+dialogue) W×4 C@mercado×2 T(compare+conjugation+more) S I×5 T(compare) C×2 C~ B×3 O Q×2`

## Урок `espanol_y_yo/me_cuesta` — «Me cuesta… Трудности и советы»

- **Цель:** сказать, что вам трудно, и дать простой совет.
- **Длина:** 25 шагов, около 11 минут. **Новая лексика:** me cuesta, el error, recordar, olvidar, el consejo, lo mejor es..., útil, fácil.
- **Интерактив:** выбор 4, ввод 6, сборка 2, пары 2, письмо 1; на слух и с голосом собеседника — 2. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 9 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | T: rule | Что вам трудно? — Me cuesta + действие или вещь: Me cuesta la pronunciación. Me cuesta en… | — |
| 2 | W | новое слово: me cuesta — мне трудно, мне тяжело даётся | — |
| 3 | W | новое слово: el error — ошибка | — |
| 4 | W | новое слово: recordar — помнить, запоминать | — |
| 5 | W | новое слово: olvidar — забывать | — |
| 6 | I: ввод | Me ___ la gramática. → cuesta | — |
| 7 | I: ввод | Me ___ las palabras largas. → cuestan | — |
| 8 | I: ввод | ¿Te ___ hablar por teléfono? → cuesta | — |
| 9 | I: ввод | A Tom le ___ los verbos. → cuestan | — |
| 10 | C~: выбор на слух | на слух «Me cuesta recordar las palabras nuevas.» → Мне трудно запоминать новые слова. | — |
| 11 | C~: выбор на слух | на слух «Siempre olvido los verbos.» → Я всегда забываю глаголы. | — |
| 12 | W | новое слово: el consejo — совет | — |
| 13 | W | новое слово: lo mejor es... — лучше всего… | — |
| 14 | W | новое слово: útil — полезный | — |
| 15 | W | новое слово: fácil — лёгкий, простой | — |
| 16 | T: compare | Как дать совет | — |
| 17 | M: пары | Проблема — совет: 4 пар (Me cuesta la pronunciaci… — Puedes escuchar música y……) | — |
| 18 | M: пары | Соедините пары: 5 пар (útil — полезный…) | — |
| 19 | B: сборка | Lo mejor es hablar mucho y no tener miedo. | — |
| 20 | B: сборка | Tienes que escuchar más español. | — |
| 21 | I: ввод | Мне трудно понимать фильмы. → Me cuesta entender las películas | — |
| 22 | I: ввод | Тебе нужно больше читать. → Tienes que leer más | — |
| 23 | O: письмо по признакам | ¿Qué te cuesta más en español? Напишите одну фразу о себе.; образец: Me cuesta entender a la gente cuando ha… | — |
| 24 | Q: тест | Me ___ los verbos. → cuestan | — |
| 25 | Q: тест | Другу трудно говорить по-испански. Какой совет вы дадите? → Lo mejor es practicar con amigos. | — |

Сигнатура: `T(rule) W×4 I×4 C~×2 W×4 T(compare) M×2 B×2 I×2 O Q×2`

## Урок `espanol_y_yo/datos` — «Анкета и алфавит»

- **Цель:** заполнить анкету и продиктовать фамилию по буквам.
- **Длина:** 28 шагов, около 11 минут. **Новая лексика:** el nombre, el apellido, la edad, la nacionalidad, la dirección, el correo electrónico, deletrear, la letra, la arroba.
- **Интерактив:** выбор 10, ввод 4, пары 1, письмо 1; на слух и с голосом собеседника — 7. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 5 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | T: text + table | Ирина записывается в языковую школу. Посмотрите на её анкету. | — |
| 2 | W | новое слово: el nombre — имя | — |
| 3 | W | новое слово: el apellido — фамилия | — |
| 4 | W | новое слово: la edad — возраст | — |
| 5 | W | новое слово: la nacionalidad — гражданство, национальность | — |
| 6 | W | новое слово: la dirección — адрес | — |
| 7 | W | новое слово: el correo electrónico — электронная почта | — |
| 8 | M: пары | Что в какой строке?: 5 пар (Nombre — Irina…) | — |
| 9 | C: выбор | irina.koval@correo.es → el correo electrónico | — |
| 10 | C: выбор | calle Mayor, 12, Madrid → la dirección | — |
| 11 | T: text + compare + compare + compare | Фамилию и почту в Испании часто просят продиктовать по буквам. У каждой буквы есть назван… | — |
| 12 | C~: выбор на слух | на слух «jota» → J | — |
| 13 | C~: выбор на слух | на слух «uve» → V | — |
| 14 | C~: выбор на слух | на слух «hache» → H | — |
| 15 | C~: выбор на слух | на слух «ge» → G | — |
| 16 | W | новое слово: deletrear — произносить по буквам | — |
| 17 | W | новое слово: la letra — буква | — |
| 18 | W | новое слово: la arroba — знак @ («собака») | — |
| 19 | C: выбор | ¿Cuántas letras tiene la palabra «hola»? → Cuatro. | — |
| 20 | T: text | В адресе почты точка — punto, знак @ — arroba: ana punto lopez arroba correo punto es — э… | — |
| 21 | I~: диктант | на слух «ka, o, uve, a, ele» → Koval | — |
| 22 | I~: диктант | на слух «erre, u, i, zeta» → Ruiz | — |
| 23 | I: ввод | ¿Cómo se escribe «Torres»? Deletrea la palabra. → te, o, erre, erre, e, ese | — |
| 24 | I: ввод | Вас зовут Олег Коваль. Secretaria: ¿Puede deletrear su apel… → ka, o, uve, a, ele | — |
| 25 | C~: выбор на слух | на слух «ana punto lopez arroba correo punto es» → ana.lopez@correo.es | — |
| 26 | O: письмо по признакам | Напишите о себе три фразы: имя и фамилия, возраст, откуда в…; образец: Me llamo Oleg Koval. Tengo treinta años… | — |
| 27 | Q: тест | Что такое «el apellido»? → фамилия | — |
| 28 | Q: тест | Какую фамилию диктуют: «ele, o, pe, e, zeta»? → López | — |

Сигнатура: `T(text+table) W×6 M C×2 T(text+compare+compare+compare) C~×4 W×3 C T(text) I~×2 I×2 C~ O Q×2`

## Урок `espanol_y_yo/lectura` — «Tres estudiantes, tres historias»

- **Цель:** понять три истории учеников и написать свою.
- **Длина:** 16 шагов, около 11 минут. **Новая лексика:** la canción, el compañero / la compañera, a menudo, la historia.
- **Интерактив:** выбор 7, ввод 2, группы 1, письмо 1; на слух и с голосом собеседника — 1. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 3 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | W | новое слово: la canción — песня | — |
| 2 | W | новое слово: el compañero / la compañera — товарищ, коллега, одноклассник | — |
| 3 | W | новое слово: a menudo — часто | — |
| 4 | W | новое слово: la historia — история, рассказ | — |
| 5 | T: text + reading | Три ученика рассказывают, зачем им испанский и что им трудно. | — |
| 6 | S: группы | ¿Quién?: Olga / Tom / Li | `historias` |
| 7 | C: выбор | ¿Cuánto tiempo hace que Tom estudia español? → Seis meses. | `historias` |
| 8 | C: выбор | ¿Para qué estudia español Li? → Para trabajar en un restaurante. | `historias` |
| 9 | C: выбор | ¿Qué le cuesta a Olga? → La gramática. | `historias` |
| 10 | C: выбор | ¿Quién practica español en el trabajo? → Olga. | `historias` |
| 11 | I: ввод | ¿Desde cuándo vive Li en Madrid? → Desde septiembre | `historias` |
| 12 | I: ввод | Как в тексте сказано «не бояться ошибок»? → no tener miedo de los errores | `historias` |
| 13 | C~: выбор на слух | на слух «Escucho canciones a menudo.» → Я часто слушаю песни. | — |
| 14 | C: выбор | Mis ___ de clase son de China y de Italia. → compañeros | — |
| 15 | C: выбор | La ___ de Olga es muy bonita: vive en Valencia y trabaja en… → historia | — |
| 16 | O: письмо по признакам | Напишите свою историю, 4–5 фраз: кто вы и откуда · давно ли…; образец: Me llamo Irina y soy de Leópolis. Hace … | — |

Сигнатура: `W×4 T(text+reading) S C@historias×4 I@historias×2 C~ C×2 O`

## Урок `espanol_y_yo/mision` — «Запись в школу и языковой обмен»

- **Цель:** записаться в языковую школу и рассказать о себе на языковом обмене.
- **Длина:** 20 шагов, около 15 минут. **Новая лексика:** нет.
- **Интерактив:** выбор 3, ввод 5, сборка 1, письмо 6; на слух и с голосом собеседника — 13. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 12 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | T: mission | Языковая школа | — |
| 2 | H: ход разговора (сборка) | Secretaria: Buenos días. ¿Quiere estudiar español aquí? → собрать: Sí, quiero estudiar español. | — |
| 3 | H: ход разговора (ввод) | Secretaria: Muy bien. ¿Cómo se llama? → написать: Me llamo Oleg Koval | — |
| 4 | H: ход разговора (ввод) | Secretaria: ¿Puede deletrear su apellido? → написать: ka, o, uve, a, ele | — |
| 5 | H: ход разговора (ввод) | Secretaria: ¿Cuántos años tiene? → написать: Tengo treinta años | — |
| 6 | H: ход разговора (ввод) | Secretaria: ¿De dónde es? → написать: Soy de Ucrania | — |
| 7 | H: ход разговора (ввод) | Secretaria: ¿Cuánto tiempo hace que estudia español? → написать: Hace un año | — |
| 8 | H: ход разговора (письмо) | Secretaria: ¿Y para qué necesita el español? → ответить от себя; образец: Para trabajar en España. | — |
| 9 | HL: лента разговора | весь разговор «В школе»; Secretaria: Perfecto. Muchas gracias. | — |
| 10 | T: text + dialogue | Вечером школа присылает вам аудио. Послушайте его: текста нет. | — |
| 11 | C: выбор | ¿Cuándo empieza la clase? → El lunes a las diez. | `mensaje` |
| 12 | C: выбор | ¿Cómo se llama la profesora? → Carmen. | `mensaje` |
| 13 | T: mission | Языковой обмен | — |
| 14 | H: ход разговора (письмо) | Diego: ¡Hola! ¿Cuánto tiempo hace que estudias español? → ответить от себя; образец: Hace un año que estudio español. | — |
| 15 | H: ход разговора (письмо) | Diego: ¿Y por qué estudias español? → ответить от себя; образец: Porque me gusta el idioma y para viajar. | — |
| 16 | H: ход разговора (письмо) | Diego: ¿Qué te cuesta más? → ответить от себя; образец: Me cuesta entender a la gente cuando ha… | — |
| 17 | H: ход разговора (письмо) | Diego: A mí me cuesta la pronunciación del inglés. ¿Tien… → ответить от себя; образец: Lo mejor es escuchar canciones en inglé… | — |
| 18 | H: ход разговора (письмо) | Diego: ¡Gracias, es un consejo muy útil! ¿Sabes hablar o… → ответить от себя; образец: Sí, sé hablar ucraniano e inglés. | — |
| 19 | H: ход разговора (выбор) | Diego: ¡Qué bien! ¿Hablamos media hora en español y medi… → выбрать: ¡Vale! ¡Perfecto! | — |
| 20 | HL: лента разговора | весь разговор «На языковом обмене»; Diego: ¡Genial! | — |

Сигнатура: `T(mission) HB HI×5 HO HL T(text+dialogue) C@mensaje×2 T(mission) HO×5 HC HL`

## Урок `espanol_y_yo/quiz` — «Тест: El español y yo»

- **Цель:** проверить цели темы — срок и цель, saber и conocer, трудности, советы, анкета.
- **Длина:** 13 шагов, около 6 минут. **Новая лексика:** нет.
- **Интерактив:** выбор 6, ввод 5, сборка 1; на слух и с голосом собеседника — 3. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 6 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | T: text + cando | Это тест по теме «El español y yo»: двенадцать заданий. | — |
| 2 | I~: диктант | на слух «Vivo en Madrid desde enero.» → Vivo en Madrid desde enero | — |
| 3 | C~: выбор на слух | на слух «Hace dos años que estudio inglés.» → Я учу английский уже два года. | — |
| 4 | C~: выбор на слух | на слух «ge, a, erre, ce, i, a» → García | — |
| 5 | I: ввод | Estudio español ___ seis meses. → desde hace | — |
| 6 | I: ввод | (yo) No ___ dónde está el banco. → sé | — |
| 7 | I: ввод | Vivo aquí desde hace un año. → Hace un año que vivo aquí | — |
| 8 | I: ввод | Скажите по-испански: «Лучше всего — много говорить». → Lo mejor es hablar mucho | — |
| 9 | B: сборка | ¿Cuánto tiempo hace que estudias español? | — |
| 10 | Q: тест | Estudio español ___ trabajar en Sevilla. → para | — |
| 11 | Q: тест | ¿___ a mi hermano? → Conoces | — |
| 12 | Q: тест | A Olga le ___ la gramática. → cuesta | — |
| 13 | Q: тест | Что такое «la dirección»? → адрес | — |

Сигнатура: `T(text+cando) I~ C~×2 I×4 B Q×4`
