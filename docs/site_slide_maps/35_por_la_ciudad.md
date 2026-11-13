# Тема 35 «Por la ciudad — по городу» · A2 — карта экранов

Цели темы: спросить и объяснить дорогу на «ты» и на «вы»; доехать на метро и сделать пересадку; попросить разрешения и о небольшой услуге; понять вывески и правила.

Карта собрана из сценария уроков (`node tools/site_map_gen.cjs --unit 35 --write`): для A2 порядок шагов
проектируется в `docs/a2_c2_curriculum_map.md` (первая тема — в `docs/a2_pilot_blueprint.md`), карта фиксирует результат.
Обозначения — `docs/site_slide_maps/README.md`.

## Урок `por_la_ciudad/perdone` — «Perdone, ¿cómo voy al museo?»

- **Цель:** понять на слух, как пройти.
- **Длина:** 19 шагов, около 8 минут. **Новая лексика:** seguir, girar, la esquina, el semáforo, cruzar, enfrente de.
- **Интерактив:** выбор 7, ввод 1, сборка 2, группы 1; на слух и с голосом собеседника — 2. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 3 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | T: text + dialogue | Том в Мадриде ищет музей Прадо и спрашивает дорогу у прохожей. Послушайте два раза: текст… | — |
| 2 | C: выбор | Далеко ли музей? → No, está a diez minutos a pie. | `prado` |
| 3 | C: выбор | Как Кармен обращается к Тому? → На «вы». | `prado` |
| 4 | W | новое слово: seguir — продолжать (путь), идти дальше | — |
| 5 | W | новое слово: girar — повернуть | — |
| 6 | W | новое слово: la esquina — угол (улицы) | — |
| 7 | W | новое слово: el semáforo — светофор | — |
| 8 | W | новое слово: cruzar — переходить (улицу) | — |
| 9 | W | новое слово: enfrente de — напротив | — |
| 10 | C: выбор | ¿Hasta dónde tiene que seguir todo recto? → Hasta el semáforo. | `prado` |
| 11 | C: выбор | ¿Qué hay en la esquina? → Una farmacia. | `prado` |
| 12 | C: выбор | ¿Qué calle tiene que tomar después? → La segunda a la izquierda. | `prado` |
| 13 | C: выбор | ¿Dónde está el museo? → Al final de la calle, enfrente de un pa… | `prado` |
| 14 | T: compare | Дорогу объясняют на «ты» и на «вы» | — |
| 15 | S: группы | «Ты» или «вы»?: tú / usted | — |
| 16 | I~: диктант | на слух «Siga todo recto hasta el semáforo.» → Siga todo recto hasta el semáforo | — |
| 17 | C~: выбор на слух | на слух «Gira a la izquierda en la esquina.» → Поверни налево на углу. | — |
| 18 | B: сборка | Cruce la calle y gire a la derecha. | — |
| 19 | B: сборка | El museo está enfrente de un parque. | — |

Сигнатура: `T(text+dialogue) C@prado×2 W×6 C@prado×4 T(compare) S I~ C~ B×2`

## Урок `por_la_ciudad/indicaciones` — «Al lado de, enfrente de, entre…»

- **Цель:** объяснить дорогу и сказать, где что находится.
- **Длина:** 19 шагов, около 8 минут. **Новая лексика:** la avenida, principal, la oficina de turismo.
- **Интерактив:** выбор 6, ввод 5, сборка 2, письмо 1; на слух и с голосом собеседника — 1. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 8 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | W | новое слово: la avenida — проспект | — |
| 2 | W | новое слово: principal — главный | — |
| 3 | W | новое слово: la oficina de turismo — туристический офис | — |
| 4 | T: table | Как объяснить дорогу | — |
| 5 | I: ввод | Sigue todo recto. → (usted) ___ todo recto. → Siga | — |
| 6 | I: ввод | Cruza la avenida. → (usted) ___ la avenida. → Cruce | — |
| 7 | I: ввод | Gira a la izquierda. → (usted) ___ a la izquierda. → Gire | — |
| 8 | I: ввод | Toma la segunda calle. → (usted) ___ la segunda calle. → Tome | — |
| 9 | T: table + note | Где находится | — |
| 10 | C: выбор | El café está ___ el banco y el cine. → entre | — |
| 11 | C: выбор | La parada está ___ hotel, al otro lado de la calle. → enfrente del | — |
| 12 | C: выбор | Hay una farmacia ___ esquina. → en la | — |
| 13 | C~: выбор на слух | на слух «La oficina de turismo está al lado del …» → Туристический офис рядом с музеем. | — |
| 14 | B: сборка | La oficina de turismo está en la avenida principal. | — |
| 15 | B: сборка | Toma la primera calle a la izquierda. | — |
| 16 | I: ввод | Банк напротив гостиницы. → El banco está enfrente del hotel | — |
| 17 | O: письмо по признакам | Объясните другу на «ты», как пройти от вашего дома до ближа…; образец: Sal de casa y gira a la derecha. Sigue … | — |
| 18 | Q: тест | El cine está ___ final de la calle. → al | — |
| 19 | Q: тест | Señora, ___ la avenida y gire a la izquierda. → cruce | — |

Сигнатура: `W×3 T(table) I×4 T(table+note) C×3 C~ B×2 I O Q×2`

## Урок `por_la_ciudad/metro` — «¿Qué línea va a Sol?»

- **Цель:** спросить и объяснить, как доехать на метро.
- **Длина:** 18 шагов, около 8 минут. **Новая лексика:** la línea, bajarse, hacer transbordo, andando.
- **Интерактив:** выбор 8, ввод 2, сборка 1, письмо 1; на слух и с голосом собеседника — 1. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 4 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | W | новое слово: la línea — линия (метро) | — |
| 2 | W | новое слово: bajarse — выходить (из транспорта) | — |
| 3 | W | новое слово: hacer transbordo — сделать пересадку | — |
| 4 | W | новое слово: andando — пешком (разг.) | — |
| 5 | T: text + dialogue | Ирина объясняет Тому, как доехать до площади Пуэрта-дель-Соль. | — |
| 6 | C: выбор | ¿Qué línea tiene que tomar Tom? → La línea uno. | `linea` |
| 7 | C: выбор | ¿Cuántas paradas son? → Cuatro. | `linea` |
| 8 | C: выбор | ¿Tiene que hacer transbordo? → No, es directo. | `linea` |
| 9 | C: выбор | ¿Dónde se baja Tom? → En Sol. | `linea` |
| 10 | C: выбор | ¿Cómo va de Sol al restaurante? → Andando. | `linea` |
| 11 | T: note | Bajarse — «выходить из транспорта», subir — «садиться». В инструкции местоимение пишется … | — |
| 12 | I: ввод | Выходи на Соль. (на «ты») → Bájate en Sol | — |
| 13 | I: ввод | Это в десяти минутах пешком. → Está a diez minutos a pie | — |
| 14 | C~: выбор на слух | на слух «Toma la línea dos y haz transbordo en S…» → Садись на вторую линию и сделай пересад… | — |
| 15 | B: сборка | Son cuatro paradas: bájate en Sol. | — |
| 16 | O: письмо по признакам | Объясните другу на «ты», как доехать от вашего дома до цент…; образец: Toma el metro, la línea tres, y bájate … | — |
| 17 | Q: тест | En Sol tienes que hacer ___ a la línea tres. → transbordo | — |
| 18 | Q: тест | La estación está ___ cinco minutos a pie. → a | — |

Сигнатура: `W×4 T(text+dialogue) C@linea×5 T(note) I×2 C~ B O Q×2`

## Урок `por_la_ciudad/permiso` — «¿Puedo…? ¿Te importa…?»

- **Цель:** попросить разрешения и о небольшой услуге.
- **Длина:** 20 шагов, около 9 минут. **Новая лексика:** ¿te importa…?, por supuesto, prohibido/a, aparcar, repetir.
- **Интерактив:** выбор 8, ввод 3, сборка 1, письмо 1; на слух и с голосом собеседника — 1. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 5 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | W | новое слово: ¿te importa…? — тебе не трудно…?, ты не против…? | — |
| 2 | W | новое слово: por supuesto — разумеется, конечно | — |
| 3 | W | новое слово: prohibido/a — запрещённый | — |
| 4 | W | новое слово: aparcar — парковаться | — |
| 5 | W | новое слово: repetir — повторять | — |
| 6 | T: table | Как попросить | — |
| 7 | C: выбор | Вы в гостях, в комнате жарко. Как попросить разрешения откр… → ¿Puedo abrir la ventana? | — |
| 8 | C: выбор | Вы не расслышали продавца. Как попросить повторить, на «вы»? → ¿Puede repetir, por favor? | — |
| 9 | C: выбор | Разрешите. → Por supuesto. | — |
| 10 | C: выбор | ¿Se puede aparcar aquí? — No, lo siento, está ___. → prohibido | — |
| 11 | T: table + note | Как ответить | — |
| 12 | C: выбор | Согласитесь. → No, claro que no. | — |
| 13 | C~: выбор на слух | на слух «¿Te importa hablar más despacio?» → Тебе не трудно говорить помедленнее? | — |
| 14 | I: ввод | Можно мне заплатить картой? → ¿Puedo pagar con tarjeta? | — |
| 15 | I: ввод | Вы можете мне помочь? (на «вы») → ¿Me puede ayudar? | — |
| 16 | I: ввод | Тебе не трудно повторить? → ¿Te importa repetir? | — |
| 17 | B: сборка | Lo siento, aquí está prohibido aparcar. | — |
| 18 | O: письмо по признакам | Напишите две вежливые просьбы: соседу по квартире (на «ты»)…; образец: Pablo, ¿te importa cerrar la ventana? H… | — |
| 19 | Q: тест | — ¿Te importa ayudarme? — No, ___. → claro que no | — |
| 20 | Q: тест | Señor, ¿___ repetir, por favor? → puede | — |

Сигнатура: `W×5 T(table) C×4 T(table+note) C C~ I×3 B O Q×2`

## Урок `por_la_ciudad/se_impersonal` — «Se habla español, se vende piso»

- **Цель:** понять вывески и объявления и сказать, что где можно.
- **Длина:** 17 шагов, около 8 минут. **Новая лексика:** vender, alquilar, el cartel.
- **Интерактив:** выбор 7, ввод 3, сборка 1, пары 1, письмо 1; на слух и с голосом собеседника — 1. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 5 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | W | новое слово: vender — продавать | — |
| 2 | W | новое слово: alquilar — снимать, сдавать (в аренду) | — |
| 3 | W | новое слово: el cartel — вывеска, объявление | — |
| 4 | T: text + table + note | Вывески и объявления часто начинаются с se: так говорят, что здесь делают или что здесь м… | — |
| 5 | M: пары | Что написано на вывеске?: 5 пар (Se habla inglés — здесь говорят по-английс……) | — |
| 6 | C: выбор | Se ___ pisos en el centro. → alquilan | — |
| 7 | C: выбор | Aquí no se ___ fumar. → puede | — |
| 8 | C: выбор | El cartel dice «Se alquila». ¿Qué significa? → Сдаётся. | — |
| 9 | C: выбор | Perdone, ¿cómo se ___ al aeropuerto? → va | — |
| 10 | C~: выбор на слух | на слух «En esta tienda se alquilan bicis por ho…» → В этом магазине можно взять велосипед н… | — |
| 11 | I: ввод | Здесь говорят по-испански. → Aquí se habla español | — |
| 12 | I: ввод | Продаётся машина. → Se vende coche | — |
| 13 | I: ввод | Как пройти к вокзалу? → ¿Cómo se va a la estación? | — |
| 14 | B: сборка | No se puede aparcar delante de la puerta. | — |
| 15 | O: письмо по признакам | Какие правила у вас дома или на работе? Напишите две-три фр…; образец: En mi casa no se puede fumar. Se puede … | — |
| 16 | Q: тест | Se ___ bicis por horas. → alquilan | — |
| 17 | Q: тест | Что значит «Se vende»? → Продаётся. | — |

Сигнатура: `W×3 T(text+table+note) M C×4 C~ I×3 B O Q×2`

## Урок `por_la_ciudad/lectura` — «Cómo llegar a mi casa»

- **Цель:** понять объяснение дороги в письме и ответить.
- **Длина:** 13 шагов, около 7 минут. **Новая лексика:** la iglesia, el ayuntamiento, el portal.
- **Интерактив:** выбор 5, ввод 2, пары 1, письмо 1; на слух и с голосом собеседника — 1. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 3 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | W | новое слово: la iglesia — церковь | — |
| 2 | W | новое слово: el ayuntamiento — мэрия | — |
| 3 | W | новое слово: el portal — подъезд, вход в дом | — |
| 4 | M: пары | Соедините пары: 3 пар (la iglesia — церковь…) | — |
| 5 | T: text + reading | Ольга пишет двоюродной сестре Наталье, как дойти до её квартиры в Валенсии. | — |
| 6 | C: выбор | ¿Qué tiene que hacer Natalia al salir de la estación? → Girar a la derecha. | `camino` |
| 7 | C: выбор | ¿Qué hay en la segunda esquina? → Un banco. | `camino` |
| 8 | C: выбор | ¿Dónde está la casa de Olga? → Enfrente de la iglesia, al lado de una … | `camino` |
| 9 | C: выбор | ¿Cuántos minutos son andando? → Quince. | `camino` |
| 10 | I: ввод | ¿En qué piso vive Olga? → En el tercero | `camino` |
| 11 | I: ввод | Как в письме сказано «поднимись на лифте»? → sube en el ascensor | `camino` |
| 12 | C~: выбор на слух | на слух «Al salir de la estación, gira a la dere…» → Выйдя из вокзала, поверни направо. | — |
| 13 | O: письмо по признакам | Вы — Наталья. Ответьте Ольге: поблагодарите, скажите, во ск…; образец: ¡Gracias, Olga! Llego a las siete. ¿Te … | — |

Сигнатура: `W×3 M T(text+reading) C@camino×4 I@camino×2 C~ O`

## Урок `por_la_ciudad/mision` — «Турист спрашивает дорогу»

- **Цель:** понять объявление в метро и объяснить дорогу туристу.
- **Длина:** 14 шагов, около 12 минут. **Новая лексика:** нет.
- **Интерактив:** выбор 4, ввод 5, письмо 2; на слух и с голосом собеседника — 5. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 7 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | I: ввод | (poner) ___ la mesa, por favor. → Pon | — |
| 2 | I: ввод | Подпишите здесь, пожалуйста. → Firme aquí, por favor | — |
| 3 | T: text + dialogue | Вы едете в метро. Послушайте объявление: текста нет. | — |
| 4 | C: выбор | ¿Cuál es la próxima parada? → Sol. | `anuncio` |
| 5 | C: выбор | ¿A qué líneas puede hacer transbordo? → A la dos y a la tres. | `anuncio` |
| 6 | C: выбор | ¿Por dónde es la salida? → Por la derecha. | `anuncio` |
| 7 | T: mission | Турист спрашивает дорогу | — |
| 8 | H: ход разговора (ввод) | Turista: Perdone, ¿hay una farmacia por aquí? → написать: Sí, en la esquina, al lado del banco | — |
| 9 | H: ход разговора (ввод) | Turista: Gracias. ¿Y para ir al Museo del Prado? → написать: Siga todo recto hasta el semáforo | — |
| 10 | H: ход разговора (ввод) | Turista: ¿Y después? → написать: Cruce la calle y gire a la izquierda | — |
| 11 | H: ход разговора (выбор) | Turista: ¿Está lejos? → выбрать: No, está a diez minutos a pie. | — |
| 12 | H: ход разговора (письмо) | Turista: ¿Se puede ir en autobús? → ответить от себя; образец: Sí, se puede: tome el autobús en esa pa… | — |
| 13 | HL: лента разговора | весь разговор «На улице»; Turista: ¡Muchas gracias! Es usted muy amable. | — |
| 14 | O: письмо по признакам | Друг впервые едет к вам. Напишите на «ты», как добраться от…; образец: Toma el metro, la línea uno, y bájate e… | — |

Сигнатура: `R×2 T(text+dialogue) C@anuncio×3 T(mission) HI×3 HC HO HL O`

## Урок `por_la_ciudad/quiz` — «Тест: Por la ciudad»

- **Цель:** проверить цели темы — дорога, метро, просьбы, вывески.
- **Длина:** 13 шагов, около 6 минут. **Новая лексика:** нет.
- **Интерактив:** выбор 4, ввод 7, сборка 1; на слух и с голосом собеседника — 3. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 8 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | T: text + cando | Это тест по теме «Por la ciudad»: двенадцать заданий. | — |
| 2 | I~: диктант | на слух «Toma la segunda calle a la derecha.» → Toma la segunda calle a la derecha | — |
| 3 | C~: выбор на слух | на слух «El banco está entre la farmacia y el ci…» → Банк между аптекой и кинотеатром. | — |
| 4 | C~: выбор на слух | на слух «¿Le importa cerrar la ventana, por favo…» → Вам не трудно закрыть окно, пожалуйста? | — |
| 5 | I: ввод | Señora, (cruzar) ___ la avenida y gire a la derecha. → cruce | — |
| 6 | I: ввод | La farmacia está enfrente ___ hotel. → del | — |
| 7 | I: ввод | En Sol tienes que hacer ___ a la línea tres. → transbordo | — |
| 8 | I: ввод | Se ___ pisos en esta calle. → alquilan | — |
| 9 | I: ввод | Можно мне открыть окно? → ¿Puedo abrir la ventana? | — |
| 10 | I: ввод | Выходи на третьей остановке. (на «ты») → Bájate en la tercera parada | — |
| 11 | B: сборка | Perdone, ¿cómo se va a la estación? | — |
| 12 | Q: тест | — ¿Te importa esperar un momento? — No, ___. → claro que no | — |
| 13 | Q: тест | Что значит «el semáforo»? → светофор | — |

Сигнатура: `T(text+cando) I~ C~×2 I×6 B Q×2`

## Урок `por_la_ciudad/control` — «Контрольная точка 2»

- **Цель:** проверить вторую треть уровня — прошлое в описании и рассказе, встречи, инструкции и дорога.
- **Длина:** 28 шагов, около 18 минут. **Новая лексика:** нет.
- **Интерактив:** выбор 13, ввод 11, письмо 1; на слух и с голосом собеседника — 2. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 12 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | T: text + cando | Контрольная точка по темам 30–35. Здесь нет нового: проверяем, что вы уже умеете. Результ… | — |
| 2 | T: text + dialogue | Том рассказывает Ирине о поездке в Толедо. Послушайте разговор два раза: текста нет. | — |
| 3 | C: выбор | ¿Qué estaba haciendo Tom cuando empezó a llover? → Paseaba por el centro. | `toledo` |
| 4 | C: выбор | ¿Por qué entró en un café? → Porque llovía y no tenía paraguas. | `toledo` |
| 5 | C: выбор | ¿Dónde vivía la señora cuando era joven? → En Madrid, en el barrio de Tom. | `toledo` |
| 6 | C: выбор | ¿Cómo era el barrio antes? → Más tranquilo y con menos coches. | `toledo` |
| 7 | C: выбор | ¿Qué propone Tom? → Ir juntos a Toledo el sábado. | `toledo` |
| 8 | C: выбор | ¿Qué tiene que llevar Tom? → Un paraguas. | `toledo` |
| 9 | I~: диктант | на слух «Antes había menos coches que ahora.» → Antes había menos coches que ahora | — |
| 10 | I~: диктант | на слух «Gire a la derecha en el semáforo.» → Gire a la derecha en el semáforo | — |
| 11 | I: ввод | De niño (yo, jugar) ___ al fútbol todos los días. → jugaba | — |
| 12 | I: ввод | Estaba en casa cuando (sonar) ___ el teléfono. → sonó | — |
| 13 | I: ввод | Mi hermano es ___ alto como mi padre. → tan | — |
| 14 | I: ввод | (tú, venir) ___ a mi casa a las ocho. → Ven | — |
| 15 | I: ввод | ¿Le prestas el coche a Pablo? — Sí, ___ presto. → se lo | — |
| 16 | I: ввод | Antes fumaba, pero ___ fumo. → ya no | — |
| 17 | C: выбор | Este café es ___ que el café de la oficina. → mejor | — |
| 18 | C: выбор | No puedo ir: ___ tengo que trabajar. → es que | — |
| 19 | C: выбор | Señor, ___ este formulario, por favor. → rellene | — |
| 20 | C: выбор | Se ___ habitaciones en este hotel. → alquilan | — |
| 21 | T: reading | Mensaje de Diego | — |
| 22 | C: выбор | ¿Cómo era el pueblo de Diego antes? → Pequeño y tranquilo. | `diego` |
| 23 | C: выбор | ¿Qué hacía Diego cuando vio a su profesora? → Paseaba por la plaza. | `diego` |
| 24 | C: выбор | ¿Qué le recomienda Diego? → Probar la comida de su madre. | `diego` |
| 25 | I: ввод | Раньше я жил в Киеве, а сейчас живу в Мадриде. → Antes vivía en Kiev y ahora vivo en Mad… | — |
| 26 | I: ввод | Хочешь пойти в кино в субботу? → ¿Te apetece ir al cine el sábado? | — |
| 27 | I: ввод | Идите прямо и поверните налево. (на «вы») → Siga todo recto y gire a la izquierda | — |
| 28 | O: письмо по признакам | Напишите 80–100 слов о месте из вашего детства: каким оно б…; образец: Cuando era pequeña, pasaba los veranos … | — |

Сигнатура: `T(text+cando) T(text+dialogue) C@toledo×6 I~×2 I×6 C×4 T(reading) C@diego×3 I×3 O`
