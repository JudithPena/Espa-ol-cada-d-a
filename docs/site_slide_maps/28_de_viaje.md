# Тема 28 «De viaje — в поездке» · A2 — карта экранов

Цели темы: купить билет на поезд и понять расписание; понять объявление на вокзале и в аэропорту; заселиться в гостиницу и решить небольшую проблему; не повторять слово: lo, la, los, las.

Карта собрана из сценария уроков (`node tools/site_map_gen.cjs --unit 28 --write`): для A2 порядок шагов
проектируется в `docs/a2_c2_curriculum_map.md` (первая тема — в `docs/a2_pilot_blueprint.md`), карта фиксирует результат.
Обозначения — `docs/site_slide_maps/README.md`.

## Урок `de_viaje/estacion` — «Un billete para Sevilla»

- **Цель:** купить билет на поезд и понять расписание.
- **Длина:** 25 шагов, около 10 минут. **Новая лексика:** el billete, de ida y vuelta, el andén, el horario, la salida, la llegada, el minuto, ¡Buen viaje!.
- **Интерактив:** выбор 11, ввод 2, сборка 1, пары 1; на слух и с голосом собеседника — 1. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 3 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | T: text + dialogue | Ирина покупает билет на вокзале в Мадриде. Послушайте разговор два раза: текста пока нет. | — |
| 2 | C: выбор | ¿Adónde va Irina? → A Sevilla. | `taquilla` |
| 3 | C: выбор | ¿Cuándo viaja? → Mañana por la mañana. | `taquilla` |
| 4 | W | новое слово: el billete — билет (на транспорт) | — |
| 5 | W | новое слово: de ida y vuelta — туда и обратно | — |
| 6 | W | новое слово: el andén — платформа, перрон | — |
| 7 | W | новое слово: ¡Buen viaje! — счастливого пути! | — |
| 8 | C: выбор | ¿A qué hora sale su tren? → A las diez. | `taquilla` |
| 9 | C: выбор | ¿Qué billete compra? → De ida y vuelta. | `taquilla` |
| 10 | C: выбор | ¿Cuánto cuesta el billete? → Setenta y cuatro euros. | `taquilla` |
| 11 | C: выбор | ¿De qué andén sale el tren? → Del cinco. | `taquilla` |
| 12 | W | новое слово: el horario — расписание | — |
| 13 | W | новое слово: la salida — отправление; выход | — |
| 14 | W | новое слово: la llegada — прибытие | — |
| 15 | W | новое слово: el minuto — минута | — |
| 16 | M: пары | Соедините пары: 6 пар (la salida — отправление…) | — |
| 17 | T: text + table | Вот расписание утренних поездов из Мадрида. | — |
| 18 | C: выбор | ¿A qué hora llega a Sevilla el tren de las diez? → 12:35 | — |
| 19 | C: выбор | ¿De qué andén sale el tren para Valencia? → Del siete. | — |
| 20 | C: выбор | Son las nueve y media. ¿Qué tren sale en diez minutos? → El de Barcelona. | — |
| 21 | I~: диктант | на слух «Un billete de ida y vuelta, por favor.» → Un billete de ida y vuelta, por favor | — |
| 22 | C: выбор | Вам нужен билет только туда. → De ida, por favor. | — |
| 23 | C: выбор | Поблагодарите. → Muchas gracias. | — |
| 24 | B: сборка | ¿De qué andén sale el tren para Sevilla? | — |
| 25 | I: ввод | Во сколько отправляется поезд на Валенсию? → ¿A qué hora sale el tren para Valencia? | — |

Сигнатура: `T(text+dialogue) C@taquilla×2 W×4 C@taquilla×4 W×4 M T(text+table) C×3 I~ C×2 B I`

## Урок `de_viaje/lo_la` — «Lo, la, los, las»

- **Цель:** заменить уже названную вещь коротким словом — lo tengo, no la encuentro.
- **Длина:** 25 шагов, около 10 минут. **Новая лексика:** la maleta, el pasaporte, encontrar, dejar, el bolso.
- **Интерактив:** выбор 7, ввод 8, сборка 2, группы 1; на слух и с голосом собеседника — 1. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 10 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | T: text + dialogue | Лусия и Пабло собираются в поездку. Какими короткими словами они заменяют вещи, чтобы не … | — |
| 2 | W | новое слово: la maleta — чемодан | — |
| 3 | W | новое слово: el pasaporte — паспорт | — |
| 4 | W | новое слово: encontrar — находить | — |
| 5 | W | новое слово: dejar — оставлять; давать на время | — |
| 6 | W | новое слово: el bolso — сумка | — |
| 7 | C: выбор | ¿Dónde están los billetes? → En la mochila. | `maletas` |
| 8 | C: выбор | ¿Dónde ha dejado Pablo el pasaporte? → En la mesa. | `maletas` |
| 9 | T: compare + more | Вместо названной вещи | — |
| 10 | S: группы | Каким словом заменить?: lo / la / los / las | — |
| 11 | I: ввод | — ¿Tienes la maleta? — Sí, ___ tengo. → la | — |
| 12 | I: ввод | — ¿Has comprado los billetes? — Sí, ___ he comprado. → los | — |
| 13 | I: ввод | — ¿Ves el andén? — No, no ___ veo. → lo | — |
| 14 | I: ввод | — ¿Dónde están las llaves? — No ___ encuentro. → las | — |
| 15 | I: ввод | — ¿Conoces a mis padres? — No, no ___ conozco. → los | — |
| 16 | I: ввод | — ¿Conoces a Carmen? — Sí, ___ conozco. → la | — |
| 17 | C: выбор | Какая фраза правильная? → No lo tengo. | — |
| 18 | C~: выбор на слух | на слух «No la encuentro.» → Я не могу её найти. | — |
| 19 | C: выбор | Вы видели его на диване. → Sí, lo he visto en el sofá. | — |
| 20 | B: сборка | No encuentro mi pasaporte. | — |
| 21 | B: сборка | ¿Dónde lo has dejado? | — |
| 22 | I: ввод | О билетах: «Я купил их вчера». → Los compré ayer | — |
| 23 | I: ввод | О чемодане (la maleta): «Я его не вижу». → No la veo | — |
| 24 | Q: тест | — ¿Tienes las llaves? — Sí, ___ tengo en el bolso. → las | — |
| 25 | Q: тест | — ¿Has dejado el pasaporte en el hotel? — No, ___ en la mal… → lo tengo | — |

Сигнатура: `T(text+dialogue) W×5 C@maletas×2 T(compare+more) S I×6 C C~ C B×2 I×2 Q×2`

## Урок `de_viaje/aeropuerto` — «En el aeropuerto»

- **Цель:** понять объявление о рейсе и зарегистрироваться на рейс.
- **Длина:** 25 шагов, около 11 минут. **Новая лексика:** el vuelo, el destino, el equipaje, facturar, la tarjeta de embarque, la puerta de embarque, el retraso, cancelado/a.
- **Интерактив:** выбор 11, ввод 2, пары 1; на слух и с голосом собеседника — 0. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 2 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | W | новое слово: el vuelo — рейс; полёт | — |
| 2 | W | новое слово: el destino — место назначения | — |
| 3 | W | новое слово: la puerta de embarque — выход на посадку | — |
| 4 | W | новое слово: el retraso — опоздание, задержка | — |
| 5 | W | новое слово: cancelado/a — отменённый | — |
| 6 | T: text + table | Табло вылетов в аэропорту Валенсии. | — |
| 7 | C: выбор | ¿De qué puerta sale el vuelo con destino a Madrid? → De la B12. | — |
| 8 | C: выбор | ¿Qué vuelo está cancelado? → El de Sevilla. | — |
| 9 | T: text + dialogue | А теперь объявления. Послушайте их два раза: текста нет. | — |
| 10 | C: выбор | ¿Cuánto retraso tiene el vuelo a Barcelona? → Una hora. | `avisos` |
| 11 | C: выбор | ¿Qué pasa con el vuelo a Sevilla? → Está cancelado. | `avisos` |
| 12 | C: выбор | Su vuelo sale a las 11:05 y tiene una hora de retraso. ¿A q… → A las doce y cinco. | `avisos` |
| 13 | W | новое слово: el equipaje — багаж | — |
| 14 | W | новое слово: facturar — сдавать в багаж; регистрировать | — |
| 15 | W | новое слово: la tarjeta de embarque — посадочный талон | — |
| 16 | T: dialogue | Регистрация на рейс | — |
| 17 | C: выбор | ¿Qué equipaje factura Irina? → Una maleta. | `mostrador` |
| 18 | C: выбор | ¿Tiene retraso su vuelo? → No, sale a su hora. | `mostrador` |
| 19 | M: пары | Соедините пары: 6 пар (el vuelo — рейс…) | — |
| 20 | C: выбор | У вас только сумка, сдавать нечего. → No, solo llevo un bolso. | — |
| 21 | C: выбор | Дайте паспорт. → Aquí lo tiene. | — |
| 22 | I: ввод | Я хочу сдать в багаж один чемодан. → Quiero facturar una maleta | — |
| 23 | I: ввод | Спросите: «Какой выход на посадку?» → ¿Cuál es la puerta de embarque? | — |
| 24 | Q: тест | El vuelo tiene dos horas de ___. → retraso | — |
| 25 | Q: тест | Что такое «la tarjeta de embarque»? → посадочный талон | — |

Сигнатура: `W×5 T(text+table) C×2 T(text+dialogue) C@avisos×3 W×3 T(dialogue) C@mostrador×2 M C×2 I×2 Q×2`

## Урок `de_viaje/ir_irse` — «Voy, me voy: ir, irse и предлоги пути»

- **Цель:** сказать, куда вы едете, откуда, на чём и когда уезжаете.
- **Длина:** 25 шагов, около 10 минут. **Новая лексика:** irse, pasar por, el avión, directo/a.
- **Интерактив:** выбор 8, ввод 8, сборка 2, письмо 1; на слух и с голосом собеседника — 2. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 11 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | T: compare | Ехать или уезжать? | — |
| 2 | W | новое слово: irse — уходить, уезжать | — |
| 3 | C: выбор | Es muy tarde. ¡___! → Me voy | — |
| 4 | C: выбор | Este verano ___ a Italia. → voy | — |
| 5 | C: выбор | — ¿Dónde está Carlos? — ___ hace una hora. → Se fue | — |
| 6 | C~: выбор на слух | на слух «¿Ya te vas?» → Ты уже уходишь? | — |
| 7 | T: table | Предлоги пути | — |
| 8 | W | новое слово: pasar por — проезжать через; заходить | — |
| 9 | W | новое слово: directo/a — прямой | — |
| 10 | W | новое слово: el avión — самолёт | — |
| 11 | I: ввод | Mañana voy ___ Sevilla. → a | — |
| 12 | I: ввод | Salgo ___ Madrid a las diez. → de | — |
| 13 | I: ввод | Siempre viajo ___ tren. → en | — |
| 14 | I: ввод | El tren no es directo: pasa ___ Córdoba. → por | — |
| 15 | I: ввод | ¿A qué hora sale el tren ___ Valencia? → para | — |
| 16 | I: ввод | Ahora estamos ___ el aeropuerto. → en | — |
| 17 | C~: выбор на слух | на слух «Se fueron ayer por la mañana.» → Они уехали вчера утром. | — |
| 18 | C: выбор | ¿El vuelo es directo? — No, ___ Madrid. → pasa por | — |
| 19 | B: сборка | Mañana me voy a Sevilla en tren. | — |
| 20 | B: сборка | Este vuelo no pasa por Madrid: es directo. | — |
| 21 | I: ввод | Я уезжаю завтра. → Me voy mañana | — |
| 22 | I: ввод | Мы едем в Валенсию на машине. → Vamos a Valencia en coche | — |
| 23 | O: письмо по признакам | ¿Cómo vas al trabajo o a clase? Напишите две фразы: на чём …; образец: Voy al trabajo en metro. Salgo de casa … | — |
| 24 | Q: тест | Viajamos ___ avión. → en | — |
| 25 | Q: тест | — ¿Te quedas? — No, ___: mañana trabajo. → me voy | — |

Сигнатура: `T(compare) W C×3 C~ T(table) W×3 I×6 C~ C B×2 I×2 O Q×2`

## Урок `de_viaje/hotel` — «En el hotel»

- **Цель:** заселиться в гостиницу и сказать, что что-то не работает.
- **Длина:** 28 шагов, около 12 минут. **Новая лексика:** la reserva, a nombre de, individual / doble, incluido/a, la planta, el ascensor, funcionar, cambiar.
- **Интерактив:** выбор 11, ввод 2, сборка 2, пары 1; на слух и с голосом собеседника — 1. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 4 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | T: text + dialogue | Ирина приехала в Севилью и заселяется в гостиницу. | — |
| 2 | W | новое слово: la reserva — бронь, бронирование | — |
| 3 | W | новое слово: a nombre de — на имя | — |
| 4 | W | новое слово: individual / doble — одноместный / двухместный | — |
| 5 | W | новое слово: incluido/a — включённый (в цену) | — |
| 6 | W | новое слово: la planta — этаж | — |
| 7 | W | новое слово: el ascensor — лифт | — |
| 8 | C: выбор | ¿Para cuántas noches es la reserva? → Para dos noches. | `recepcion` |
| 9 | C: выбор | ¿Dónde es el desayuno? → En la planta baja. | `recepcion` |
| 10 | C: выбор | ¿Qué número tiene la habitación? → 305 | `recepcion` |
| 11 | C: выбор | ¿Qué le piden a Irina? → El pasaporte. | `recepcion` |
| 12 | T: note | Этажи считают порядковыми словами: la primera planta, la segunda, la tercera, la cuarta, … | — |
| 13 | C: выбор | У вас бронь на имя Олега Коваля. → Sí, a nombre de Oleg Koval. | — |
| 14 | C~: выбор на слух | на слух «Su habitación está en la segunda planta.» → Ваш номер на втором этаже. | — |
| 15 | C: выбор | Вас двое. Какой номер вы попросите? → Una habitación doble. | — |
| 16 | T: text | Через час Ирина снова у стойки. | — |
| 17 | T: dialogue | Проблема | — |
| 18 | W | новое слово: funcionar — работать (о технике) | — |
| 19 | W | новое слово: cambiar — менять | — |
| 20 | C: выбор | ¿Qué problema tiene Irina? → La ducha no funciona. | `problema` |
| 21 | C: выбор | ¿Qué habitación tiene ahora? → La 207. | `problema` |
| 22 | M: пары | Соедините пары: 6 пар (la reserva — бронь…) | — |
| 23 | B: сборка | Tengo una reserva a nombre de Ana López. | — |
| 24 | B: сборка | ¿El desayuno está incluido? | — |
| 25 | I: ввод | Телевизор не работает. → La tele no funciona | — |
| 26 | I: ввод | Спросите: «Можно поменять номер?» → ¿Puedo cambiar de habitación? | — |
| 27 | Q: тест | Tengo una reserva ___ Carlos Ruiz. → a nombre de | — |
| 28 | Q: тест | El ascensor no ___: tenemos que subir a pie. → funciona | — |

Сигнатура: `T(text+dialogue) W×6 C@recepcion×4 T(note) C C~ C T(text) T(dialogue) W×2 C@problema×2 M B×2 I×2 Q×2`

## Урок `de_viaje/lectura` — «Opiniones: dos hoteles»

- **Цель:** понять отзывы о гостиницах и написать свой.
- **Длина:** 21 шаг, около 13 минут. **Новая лексика:** limpio/a, sucio/a, el ruido, amable, recomendar, el/la recepcionista, la opinión.
- **Интерактив:** выбор 8, ввод 2, пары 1, группы 1, письмо 1; на слух и с голосом собеседника — 1. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 3 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | W | новое слово: limpio/a — чистый | — |
| 2 | W | новое слово: sucio/a — грязный | — |
| 3 | W | новое слово: el ruido — шум | — |
| 4 | W | новое слово: amable — любезный, приветливый | — |
| 5 | M: пары | Соедините пары: 4 пар (limpio — чистый…) | — |
| 6 | W | новое слово: recomendar — советовать, рекомендовать | — |
| 7 | W | новое слово: el/la recepcionista — администратор гостиницы | — |
| 8 | W | новое слово: la opinión — мнение; отзыв | — |
| 9 | C: выбор | — ¿Conoces un buen hotel en Sevilla? — Sí, te ___ el Hotel … → recomiendo | — |
| 10 | C: выбор | He leído muchas ___ de este hotel: a todos les gusta. → opiniones | — |
| 11 | T: text + reading | Перед поездкой Ирина читает отзывы о двух гостиницах Севильи. | — |
| 12 | S: группы | О какой гостинице это сказано?: Hotel Sol / Hotel Luna | `opiniones` |
| 13 | C: выбор | ¿Cuántas noches estuvo Olga en el hotel? → Tres. | `opiniones` |
| 14 | C: выбор | ¿Qué hizo la recepcionista del Hotel Sol? → Recomendó un restaurante. | `opiniones` |
| 15 | C: выбор | ¿Por qué Tom no pudo dormir? → Porque hubo mucho ruido en la calle. | `opiniones` |
| 16 | C: выбор | ¿Quién recomienda su hotel? → Olga. | `opiniones` |
| 17 | I: ввод | ¿Cuánto cuesta el desayuno en el Hotel Luna? → Ocho euros | `opiniones` |
| 18 | I: ввод | Как Ольга пишет «Рекомендую (эту гостиницу)!»? → Lo recomiendo | `opiniones` |
| 19 | C~: выбор на слух | на слух «La habitación es pequeña, pero muy limp…» → Номер маленький, но очень чистый. | — |
| 20 | C: выбор | El baño está muy ___: quiero cambiar de habitación. → sucio | — |
| 21 | O: письмо по признакам | Напишите отзыв о гостинице или квартире, где вы останавлива…; образец: Estuve dos noches en el Hotel Sol de Se… | — |

Сигнатура: `W×4 M W×3 C×2 T(text+reading) S C@opiniones×4 I@opiniones×2 C~ C O`

## Урок `de_viaje/mision` — «Билет и заселение»

- **Цель:** купить билет на вокзале и заселиться в гостиницу.
- **Длина:** 19 шагов, около 12 минут. **Новая лексика:** нет.
- **Интерактив:** выбор 4, ввод 8, сборка 1, письмо 1; на слух и с голосом собеседника — 10. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 10 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | I: ввод | En 2020 (nosotros, estar) ___ en Italia. → estuvimos | — |
| 2 | I: ввод | Carlos todavía no ha (volver) ___. → vuelto | — |
| 3 | T: mission | На вокзале | — |
| 4 | H: ход разговора (ввод) | Empleado: Buenos días. ¿Adónde viaja? → написать: A Valencia | — |
| 5 | H: ход разговора (ввод) | Empleado: ¿Para cuándo? → написать: Para mañana por la mañana | — |
| 6 | H: ход разговора (выбор) | Empleado: Hay un tren a las nueve y cuarto y otro a las onc… → выбрать: El de las nueve y cuarto. | — |
| 7 | H: ход разговора (сборка) | Empleado: ¿De ida o de ida y vuelta? → собрать: De ida y vuelta, por favor. | — |
| 8 | H: ход разговора (ввод) | Empleado: Son cuarenta y dos euros. → написать: ¿De qué andén sale el tren? | — |
| 9 | HL: лента разговора | весь разговор «В кассе»; Empleado: Del andén tres. ¡Buen viaje! | — |
| 10 | T: text + dialogue | Вы уже на вокзале. Звучит объявление. Послушайте его два раза: текста нет. | — |
| 11 | C: выбор | ¿Qué pasa con el tren a Valencia? → Tiene veinte minutos de retraso. | `aviso` |
| 12 | C: выбор | ¿De qué andén sale ahora? → Del siete. | `aviso` |
| 13 | T: mission | В гостинице | — |
| 14 | H: ход разговора (ввод) | Recepcionista: Buenas noches. ¿Tiene una reserva? → написать: Sí, a nombre de Oleg Koval | — |
| 15 | H: ход разговора (ввод) | Recepcionista: Una habitación doble para tres noches, ¿verdad? → написать: No, individual para dos noches | — |
| 16 | H: ход разговора (выбор) | Recepcionista: Perdone. Aquí está: individual, dos noches. ¿Me d… → выбрать: Sí, aquí lo tiene. | — |
| 17 | H: ход разговора (ввод) | Recepcionista: Gracias. Su habitación es la 412, en la cuarta pl… → написать: ¿El desayuno está incluido? | — |
| 18 | H: ход разговора (письмо) | Recepcionista: Sí, es de siete a diez, en la planta baja. → ответить от себя; образец: ¿Hay ascensor? | — |
| 19 | HL: лента разговора | весь разговор «Заселение»; Recepcionista: Claro. ¡Buenas noches! | — |

Сигнатура: `R×2 T(mission) HI×2 HC HB HI HL T(text+dialogue) C@aviso×2 T(mission) HI×2 HC HI HO HL`

## Урок `de_viaje/quiz` — «Тест: De viaje»

- **Цель:** проверить цели темы — билет, расписание, гостиница, lo / la, предлоги.
- **Длина:** 14 шагов, около 6 минут. **Новая лексика:** нет.
- **Интерактив:** выбор 5, ввод 7, сборка 1; на слух и с голосом собеседника — 3. **Самостоятельное воспроизведение:** ввод, сборка и письмо — 8 заданий.

| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |
|---|---|---|---|
| 1 | T: text + cando | Это тест по теме «De viaje»: тринадцать заданий. | — |
| 2 | I~: диктант | на слух «El tren sale del andén cinco.» → El tren sale del andén cinco | — |
| 3 | C~: выбор на слух | на слух «El vuelo con destino a Madrid tiene dos…» → Рейс в Мадрид задерживается на два часа. | — |
| 4 | C~: выбор на слух | на слух «Tengo una reserva a nombre de Ana López.» → У меня бронь на имя Аны Лопес. | — |
| 5 | I: ввод | — ¿Tienes los billetes? — Sí, ___ tengo. → los | — |
| 6 | I: ввод | — ¿Has visto mi maleta? — No, no ___ he visto. → la | — |
| 7 | I: ввод | Salimos ___ Madrid a las ocho. → de | — |
| 8 | I: ввод | El tren pasa ___ Córdoba. → por | — |
| 9 | I: ввод | Душ не работает. → La ducha no funciona | — |
| 10 | I: ввод | Я уезжаю завтра. → Me voy mañana | — |
| 11 | B: сборка | Un billete de ida y vuelta para Sevilla. | — |
| 12 | Q: тест | Viajamos ___ tren. → en | — |
| 13 | Q: тест | El vuelo está ___: hoy no sale. → cancelado | — |
| 14 | Q: тест | — ¿El desayuno está incluido? — No, ___ ocho euros. → cuesta | — |

Сигнатура: `T(text+cando) I~ C~×2 I×6 B Q×3`
