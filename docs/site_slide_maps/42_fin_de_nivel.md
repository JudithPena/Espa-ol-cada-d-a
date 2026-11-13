# Тема 42 «Итог A2» · A2 — карта экранов

Цели темы: повторить весь уровень A2 в одной поездке; прочитать рассказ о поездке и написать свой — 100–120 слов; сдать итоговый тест уровня A2.

Карта собрана из сценария уроков (`node tools/site_map_gen.cjs --unit 42 --write`): для A2 порядок шагов
проектируется в `docs/a2_c2_curriculum_map.md` (первая тема — в `docs/a2_pilot_blueprint.md`), карта фиксирует результат.
Обозначения — `docs/site_slide_maps/README.md`.

## Урок `fin_de_nivel/repaso` — «Большое повторение A2: выходные в Саламанке»

- **Цель:** провести выходные в Саламанке — от вокзала до звонка другу — на материале всего уровня.
- **Длина:** 20 шагов, около 9 минут. **Новая лексика:** нет.
- **Интерактив:** выбор 9, ввод 3, сборка 1; на слух и с голосом собеседника — 2. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 4 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | T: text | Новых слов нет: всё, что нужно, вы уже знаете. Проведите выходные в Саламанке — шесть сит… | — |
| 2 | T: mission | Вокзал | — |
| 3 | C: выбор | Вам нужен билет туда и обратно до Саламанки, на сегодня. → Un billete de ida y vuelta para Salaman… | `estacion` |
| 4 | C~: выбор на слух | на слух «El tren sale a las cinco y cuarto del a…» → в четверть шестого, с третьей платформы | `estacion` |
| 5 | T: mission | Гостиница | — |
| 6 | C: выбор | Ответьте: да, вы забронировали двухместный номер на две ноч… → Sí, he reservado una habitación doble p… | `hotel` |
| 7 | I: ввод | Позвоните на ресепшен и скажите: «В моём номере не работает… → En mi habitación no funciona la ducha | `hotel` |
| 8 | T: mission | Дорога | — |
| 9 | B: сборка | Perdone, ¿cómo se va a la Plaza Mayor? | `camino` |
| 10 | C~: выбор на слух | на слух «Siga todo recto y gire a la izquierda e…» → прямо, у второго светофора налево, пять… | `camino` |
| 11 | T: mission | Аптека | — |
| 12 | C: выбор | Buenas tardes. ¿Qué le pasa? → Me encuentro mal: me duele el estómago. | `farmacia` |
| 13 | C: выбор | Что советует фармацевт? → пить много воды и немного отдохнуть | `farmacia` |
| 14 | T: mission | Магазин | — |
| 15 | I: ввод | Скажите продавцу: «Я хотел(а) бы поменять эту рубашку: она … → Quería cambiar esta camisa: es pequeña | `tienda` |
| 16 | C: выбор | ¿Tiene usted el tique? → Sí, aquí lo tiene. | `tienda` |
| 17 | T: mission | Звонок Диего | — |
| 18 | C: выбор | ¿Qué has hecho hoy? → He visitado la universidad y he comido … | `llamada` |
| 19 | C: выбор | ¿Y qué te parece Salamanca? ¿Es más bonita que Madrid? → Es tan bonita como Madrid, pero más tra… | `llamada` |
| 20 | I: ввод | Diego: ¿Y qué vas a hacer mañana? — «Если будет хорошая пог… → Si hace buen tiempo, voy a ir al parque | `llamada` |

Сигнатура: `T(text) T(mission) C@estacion C~@estacion T(mission) C@hotel I@hotel T(mission) B C~@camino T(mission) C@farmacia×2 T(mission) I@tienda C@tienda T(mission) C@llamada×2 I@llamada`

## Урок `fin_de_nivel/lectura` — «Un viaje inolvidable»

- **Цель:** прочитать рассказ о поездке и найти в нём все времена A2.
- **Длина:** 12 шагов, около 6 минут. **Новая лексика:** inolvidable, lleno/a.
- **Интерактив:** выбор 6, ввод 2, группы 1; на слух и с голосом собеседника — 1. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 2 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | W | новое слово: inolvidable — незабываемый | — |
| 2 | W | новое слово: lleno/a — полный, заполненный | — |
| 3 | T: text + reading | Ирина пишет в блог о поездке в Кордову. | — |
| 4 | C: выбор | ¿Cuándo llegaron a Córdoba? → El viernes por la noche. | `cordoba` |
| 5 | C: выбор | ¿Cómo era el hotel? → Una casa antigua con un patio. | `cordoba` |
| 6 | C: выбор | ¿Qué pasó mientras hacían fotos? → Olga perdió su cartera. | `cordoba` |
| 7 | C: выбор | ¿Cómo es Córdoba para Irina? → Más pequeña y más tranquila que Madrid. | `cordoba` |
| 8 | C: выбор | ¿Cuándo es mejor ir a Córdoba? → En primavera. | `cordoba` |
| 9 | S: группы | Как было или что случилось?: как было (фон) / что случилось (событие) | `cordoba` |
| 10 | I: ввод | Как в тексте сказано «Это была незабываемая поездка»? → Fue un viaje inolvidable | `cordoba` |
| 11 | I: ввод | ¿Qué compró Irina para su familia? → Recuerdos | `cordoba` |
| 12 | C~: выбор на слух | на слух «Los patios de Córdoba están llenos de f…» → Дворики Кордовы полны цветов. | — |

Сигнатура: `W×2 T(text+reading) C@cordoba×5 S I@cordoba×2 C~`

## Урок `fin_de_nivel/proyecto` — «Рассказ о поездке»

- **Цель:** рассказать о своей поездке в разговоре и письменно — итоговый проект A2.
- **Длина:** 10 шагов, около 10 минут. **Новая лексика:** нет.
- **Интерактив:** выбор 1, ввод 1, сборка 1, письмо 5; на слух и с голосом собеседника — 5. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 7 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | B: сборка | Nos entendemos sin problemas: es la misma lengua. | — |
| 2 | C: выбор | En Argentina se ___ mucha carne. → come | — |
| 3 | T: mission | Рассказ о поездке | — |
| 4 | H: ход разговора (письмо) | Diego: ¿Cuál es el mejor viaje de tu vida? ¿Adónde fuist… → ответить от себя; образец: Fui a Valencia el verano pasado con mi … | — |
| 5 | H: ход разговора (письмо) | Diego: ¿Y cómo era? ¿Qué tiempo hacía? → ответить от себя; образец: Era una ciudad muy bonita, con playa. H… | — |
| 6 | H: ход разговора (письмо) | Diego: ¿Pasó algo especial? → ответить от себя; образец: Mientras paseábamos por la playa, de re… | — |
| 7 | H: ход разговора (письмо) | Diego: ¡Qué bien! Yo también quiero ir. ¿Qué me recomien… → ответить от себя; образец: Te recomiendo ir en primavera. Prueba l… | — |
| 8 | H: ход разговора (ввод) | Diego: ¿Y te gustaría volver? → написать: Sí, me gustaría mucho volver el año que… | — |
| 9 | HL: лента разговора | весь разговор «Разговор с Диего»; Diego: ¡Entonces la próxima vez vamos juntos! | — |
| 10 | O: письмо по признакам | Итоговый проект A2. Напишите рассказ о поездке, 100–120 сло…; образец: El verano pasado fui a Valencia con mi … | — |

Сигнатура: `R×2 T(mission) HO×4 HI HL O`

## Урок `fin_de_nivel/examen` — «Итоговый тест A2»

- **Цель:** проверить весь уровень: слух, чтение и формы.
- **Длина:** 30 шагов, около 14 минут. **Новая лексика:** нет.
- **Интерактив:** выбор 17, ввод 8, сборка 2; на слух и с голосом собеседника — 2. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 10 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | T: text | Итоговый тест уровня A2: слух, чтение и формы — двадцать семь заданий. Чтобы завершить ур… | — |
| 2 | T: text + dialogue | Слух. Ирина рассказывает Диего о выходных. Послушайте разговор два раза: текста нет. | — |
| 3 | C: выбор | ¿Dónde ha estado Irina? → En Segovia, con Olga. | `segovia` |
| 4 | C: выбор | ¿Qué tiempo hacía? → Frío, pero no llovía. | `segovia` |
| 5 | C: выбор | ¿Qué pasó el domingo? → El autobús llegó tarde y empezó a nevar. | `segovia` |
| 6 | C: выбор | ¿Por qué no puede ir Irina al cine el jueves? → Porque tiene clase. | `segovia` |
| 7 | C: выбор | ¿Qué va a hacer Diego si no hay entradas? → Llamar a Irina. | `segovia` |
| 8 | I~: диктант | на слух «Cuando era pequeña, vivía en un pueblo …» → Cuando era pequeña, vivía en un pueblo … | — |
| 9 | I~: диктант | на слух «Si tienes tiempo, ven a mi casa el sába…» → Si tienes tiempo, ven a mi casa el sába… | — |
| 10 | I: ввод | Ayer (nosotros, ir) ___ al cine. → fuimos | — |
| 11 | I: ввод | De niño (yo, jugar) ___ en la calle con mis amigos. → jugaba | — |
| 12 | I: ввод | ¿(Tú, estar) ___ alguna vez en México? → Has estado | — |
| 13 | I: ввод | Mi hermana es ___ alta como yo. → tan | — |
| 14 | I: ввод | ¿Le has comprado el regalo a tu madre? — Sí, ya ___ he comp… → se lo | — |
| 15 | I: ввод | Si (llover) ___ mañana, nos quedamos en casa. → llueve | — |
| 16 | C: выбор | Mientras ___ la tele, sonó el teléfono. → veía | — |
| 17 | C: выбор | Señora, ___ la segunda calle a la derecha. → tome | — |
| 18 | C: выбор | Buenos días, ___ reservar una mesa para dos, por favor. → me gustaría | — |
| 19 | C: выбор | Estos zapatos cuestan trescientos euros: son ___. → carísimos | — |
| 20 | C: выбор | Esta maleta no es mía, es ___. → tuya | — |
| 21 | C: выбор | Hoy Pablo ___ muy nervioso: tiene un examen. → está | — |
| 22 | C: выбор | En España ___ muy tarde: a las diez o a las once. → se cena | — |
| 23 | C: выбор | Estudio español ___ hace tres años. → desde | — |
| 24 | T: text + reading | Чтение. Ольга пишет Ирине. | — |
| 25 | C: выбор | ¿Por qué está cansada Olga? → Ha trabajado mucho esta semana. | `olga` |
| 26 | C: выбор | ¿Qué propone Olga a Irina y a Diego? → Dormir en su casa después de la cena. | `olga` |
| 27 | C: выбор | ¿Cómo es el piso nuevo de Olga? → Más grande que el antiguo. | `olga` |
| 28 | C: выбор | ¿Qué le pide Olga a Irina? → Devolver el libro. | `olga` |
| 29 | B: сборка | Te recomiendo visitar el centro por la mañana. | — |
| 30 | B: сборка | Cuando llegamos, estaba lloviendo. | — |

Сигнатура: `T(text) T(text+dialogue) C@segovia×5 I~×2 I×6 C×8 T(text+reading) C@olga×4 B×2`

## Урок `fin_de_nivel/fin` — «¡Enhorabuena! Уровень A2»

- **Цель:** увидеть, чему вы научились на уровне A2, и выбрать, что делать дальше.
- **Длина:** 8 шагов, около 3 минут. **Новая лексика:** ¡Lo has conseguido!, ¡Sigue así!.
- **Интерактив:** выбор 3; на слух и с голосом собеседника — 0. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 0 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | T: text | ¡Enhorabuena! Вы прошли уровень A2: девятнадцать тем, больше ста сорока уроков и почти пя… | — |
| 2 | W | новое слово: ¡Lo has conseguido! — у тебя получилось! ты добился своего! | — |
| 3 | W | новое слово: ¡Sigue así! — так держать! продолжай в том же духе! | — |
| 4 | T: cando |  | — |
| 5 | T: header + list | Что дальше? | — |
| 6 | C: выбор | ¡Enhorabuena! Ya has terminado las lecciones de A2. → ¡Muchas gracias! | — |
| 7 | C: выбор | Как сказать другу «У тебя получилось!»? → ¡Lo has conseguido! | — |
| 8 | C: выбор | Как сказать «Так держать!»? → ¡Sigue así! | — |

Сигнатура: `T(text) W×2 T(cando) T(header+list) C×3`
