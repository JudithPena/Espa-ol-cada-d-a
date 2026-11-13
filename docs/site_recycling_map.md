# Карта возврата лексики A0–A1

Аудит MYTHOS, SYS-08: слово, которое после своей темы больше не звучит в текстах и диалогах, держится только на
интервальном повторении во вкладке «Повторить». Эта карта показывает, где слова прошлых тем возвращаются в уроки, и
служит списком задач для правок. Составлена 13 ноября 2026, на этапе ремонта Э6 (журнал —
[`docs/a0_a1_repair_progress.md`](a0_a1_repair_progress.md)).

## Как проверить

```bash
python3 tools/audit/course_scan.py recycle -v --window 5
```

Слово считается встреченным в уроке, если в любом тексте урока стоит любая его форма: множественное число, любое время
глагола, возвратный инфинитив. В тексты урока входят реплики, чтение, вопросы, варианты ответов, пояснения. Колонки
отчёта: «не встречаются в других темах», «ни разу после своего урока» и «не возвращаются в ближайших N темах». Сканер
только читает, в `validate` и CI не подключён: показатель — повод посмотреть урок, а не ошибка.

## Состояние на 13 ноября 2026

- **Ни разу больше не встречаются:** содержательных слов A0–A1 — 0. В отчёте остаются короткие служебные слова (sí, no,
  tú, yo, él, mi, tu, su, en, a, o, e, ya, el té). Сканер не считает слова короче трёх букв, а все они звучат постоянно.
  До ремонта было 212 из 613 (аудит), после этапов Э5 и Э6 — 31; эти 31 слово вписаны в тексты и диалоги следующих тем
  (таблица ниже).
- **Старые слова в каждой теме:** в темах 02–23 звучит от 16 до 313 слов прошлых тем, в теме 01 — 6. В теме 00 всего
  20 слов на произношение, а тема 01 — приветствия. Цель этапа Э6 (10–15 старых слов в теме) выполнена.
- **Не возвращаются в ближайших пяти темах:** 209 слов A0–A1 (список внизу). Они звучат позже, в основном в итогах A0
  и A1 и в уроках A2. Это запас для правок, а не ошибки.

## Возвращено 13 ноября 2026

Слово стоит в новой фразе текста или реплике диалога; вопросы к текстам проверены, ответы не изменились.

| Слово (тема) | Где звучит теперь |
|---|---|
| repite, No entiendo (03) | 05 `paises/dialogo`: «Perdón, no entiendo. Repite, por favor.» — Диего повторяет вопрос |
| la respuesta, la traducción, el repaso (03); el tema, el vocabulario (09) | 22 `experiencias/lectura`: «Los fines de semana hago un repaso del vocabulario. En clase escribo las respuestas en español y casi nunca necesito la traducción»; «He aprendido a hablar de muchos temas» |
| trece (04) | 08 `familia/lectura`: двоюродный брат Луис — «Luis tiene trece años» |
| americano/a (05) | 10 `casa/lectura`: «Me llamo Sara. Soy americana…» |
| la lámpara (06) | 10 `casa/lectura`: в гостиной — «una mesa, cuatro sillas y una lámpara» |
| el cuaderno (06) | 10 `casa/escucha`: «En la mesa hay un libro, un cuaderno y unas gafas» (и вариант теста) |
| el programador, el abogado (07) | 12 `ciudad/lectura`: «Soy programador…», «Mi amiga Clara es abogada…» |
| inteligente (09) | 14 `gustos/lectura`: «¿Eres simpático e inteligente?» (заодно y → e) |
| castaño/a (09) | 19 `planes/lectura`: парень Натальи — «tiene el pelo castaño» |
| el balcón, la cama, el armario, la estantería (10) | 11 `ser_estar/dialogo`: новая квартира Аны — «un balcón pequeño… una cama grande, un armario y una estantería» |
| encima de, debajo de, la cama (10) | 16 `rutina/lectura`: «Mis gafas están siempre encima de la mesa, al lado de la cama», «mi gato duerme debajo de la cama» |
| el refresco, el té (13) | 16 `rutina/lectura`: «tomamos un refresco en un bar», «después tomamos un té»; 20 `salud/medico`: «beber mucha agua y té» |
| peinarse (16) | 21 `ahora/llamada`: «Me estoy peinando: esta noche voy a una fiesta» |
| ahí (17) | 19 `planes/invitacion`: «¡Perfecto! Nos vemos ahí» |
| el probador, la talla (17) | 22 `experiencias/lectura`: «En la tienda entiendo palabras como «la talla» o «el probador»» |
| la fecha, el clima, el otoño (18) | 19 `planes/lectura`: «La fecha del viaje…», «En agosto el clima es muy bueno para la playa», «en otoño tienes que visitar Kiev» |
| el cuerpo, el brazo, la espalda (20) | 23 `final/lectura`: «me duele todo el cuerpo: la espalda, los brazos, las piernas…» |

Ещё слова прошлых тем возвращаются в новых заданиях `final/repaso` (24 задания, темы 9–11, 14–16, 18 — U23-04),
`paises/repaso` (15 заданий, ввод по каждой из тем 1–5 — U05-05) и итогов A0 и A1 (этап Э5).

## Правило для новых и исправляемых уроков

- В тексте или диалоге темы N — 2–4 слова из списка ниже для тем N−5 … N−1, если они естественно ложатся в сюжет.
  Новых заданий для этого не нужно: достаточно фразы в тексте или реплики.
- Слово, которое ученик ещё не проходил, нельзя (это проверяет `validate`); форму, которой он не знает, тоже нельзя.
  Пример: `ropa` в теме 16 — нельзя, одежду проходят в теме 17; `cada`, `todas` в A1 — нельзя.
- Персонажи — по [таблице](site_characters.md): возвращённое слово не должно менять биографию постоянного героя.
- После правки — `python3 tools/audit/course_scan.py recycle -v --window 5` и `python -m espanol validate`.

## Запас: слова, которые не возвращаются в ближайших пяти темах

Строка — тема, где слово введено. Короткие служебные слова (sí, no, tú, mi…) можно не учитывать.

| Тема | Слова |
|---|---|
| 00 | sí, no, el hotel, la música, el jamón, la guitarra, la paella, la tortilla, la cerveza, la plaza |
| 01 | regular, mal, tú, de nada, no pasa nada |
| 02 | igualmente, yo, él |
| 03 | escucha, lee, escribe, la respuesta, el texto, la traducción, el repaso, el apellido, practica |
| 04 | cero, seis, siete, once, quince, dieciséis, dieciocho, diecinueve, ochenta, noventa, cien, el número, el teléfono, mi, tu, su |
| 05 | México, Francia, Inglaterra, Estados Unidos, China, chino/a, e, en |
| 06 | o, el ordenador, el reloj, la botella, el dinero |
| 07 | el enfermero / la enfermera, escuchar |
| 08 | el hijo / la hija, nuestro/a, vuestro/a, el tío / la tía, el marido |
| 09 | la lección, el tema, el chico / la chica, bajo/a, joven, rubio/a, guapo/a, delgado/a, tímido/a, trabajador/a, bastante, blanco/a, negro/a, marrón, el ojo, el pelo, largo/a, corto/a, castaño/a, llevar, mejor |
| 10 | el salón, el sofá, la ducha, encima de, debajo de, delante de, detrás de, allí, viejo/a, cómodo/a, ¿cuántos? / ¿cuántas?, mamá / papá, el nombre, la dirección, el correo electrónico, la arroba, la nacionalidad, la edad |
| 11 | contento/a, triste, nervioso/a, enfermo/a, ocupado/a, aburrido/a, porque, el jefe / la jefa |
| 12 | la ciudad, la tienda, el supermercado, el banco, la estación, la parada, ¿Adónde vas?, a, el aeropuerto, el tren, a pie, todo recto, a la derecha, a la izquierda, el mercado, el barrio, tranquilo/a |
| 13 | el agua, el té, el zumo, el pan, la carne, el pollo, el arroz, la ensalada, la sopa, el huevo, la patata, el tomate, la naranja, el plátano, la verdura, escribir, la comida, algo, el bocadillo |
| 14 | bailar, cantar, correr, el deporte, el baloncesto, la serie, a mí también, me encanta, no... nada, el intercambio, practicar, difícil, la idea |
| 15 | el martes, el jueves, en punto, terminar, abierto/a, cerrado/a |
| 16 | despertarse, salir, afeitarse, volver, acostarse, antes de, nunca |
| 17 | la camisa, la falda, el vestido, el jersey, mil, el abrigo, ese/esa, aquel/aquella, el precio, el céntimo, gris, me lo llevo / me la llevo, pagar, la tarjeta |
| 18 | la primavera, favorito/a, el mes, el norte, el sur |
| 19 | próximo/a |
| 20 | la mano, el estómago, la muela, el resfriado, la receta |
| 21 | ¿Diga?, oye |
| 22 | ya, el mar |
| 23 | ¡Enhorabuena!, ¡Mucha suerte! |
