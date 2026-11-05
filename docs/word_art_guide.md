# Картинки к словам (сайт, A0–A1)

Картинка слова хранится в `content/art/<slug>.webp` (360×360). Соответствие слов и файлов задаёт `ART_SLUGS` в `espanol/site.py`.

Без картинки на карточке стоит значок. Картинки добавляем постепенно, удачные не меняем. Первыми делаем слова,
где картинка правда помогает запомнить: люди, предметы, жесты, ситуации.

Стиль — тот же, что у уже нарисованных слов и аватаров персонажей диалогов: плоская векторная иллюстрация,
тёплые пастельные цвета. Люди на картинках — наши персонажи (Lucía, Pablo, Señor García…), чтобы ученик их узнавал.

Лист из ChatGPT — сетка 3×3. Режем его по сетке слева направо, сверху вниз, затем вписываем слова в `ART_SLUGS`.

## Общий стиль (в начало промпта)

> Flat vector illustration, warm pastel colours, soft rounded shapes, simple friendly faces, same style for every
> picture. A square image divided into a 3×3 grid of equal square cells separated by thin white gaps. Each cell is a
> small scene on a plain soft cream background, centred, with generous margins. No text, no letters, no speech
> bubbles with words, no frames.
>
> Recurring characters (draw them the same in every cell where they appear): Lucía — Spanish woman, about 25, long
> dark-brown wavy hair, mustard sweater. Pablo — Spanish man, about 27, short dark hair, short neat beard,
> light-blue shirt. Señor García — elderly man, about 70, white hair and white moustache, brown flat cap,
> brown jacket.

## Лист 1 — «ты», «вы» и вежливые фразы (тема 1–2)

Порядок: `tu usted yo el ella muchas_gracias de_nada hasta_luego hasta_manana`

1. tú — Lucía smiles and points with an open hand at Pablo, two friends talking casually.
2. usted — Lucía politely greets Señor García with a slight respectful nod.
3. yo — Pablo points at his own chest with a smile.
4. él — Lucía points to Pablo, who stands a little to the side.
5. ella — Pablo points to Lucía, who stands a little to the side.
6. muchas gracias — Lucía holds a gift box and thanks Pablo warmly, hand on heart.
7. de nada — Pablo shrugs kindly with open palms, smiling.
8. hasta luego — Pablo waves goodbye while walking away, the sun is still high.
9. hasta mañana — Lucía waves goodbye at a door in the evening, a small crescent moon in the sky.

## Лист 2 — знакомство и команды на уроке (темы 2–3)

Порядок: `me_llamo como_te_llamas encantado mucho_gusto escucha repite lee escribe responde`

1. me llamo… — Pablo smiles and shakes hands, introducing himself, his other hand on his chest.
2. ¿Cómo te llamas? — Lucía asks Pablo a question with a curious friendly look, palm open towards him.
3. encantado/a — Lucía and Pablo shake hands, both smiling happily.
4. mucho gusto — Señor García shakes hands politely with Pablo.
5. escucha — Lucía listens carefully, hand cupped behind her ear.
6. repite — Pablo speaks, a small curved double arrow (repeat symbol) next to him, no letters.
7. lee — Lucía reads an open book.
8. escribe — Pablo writes in a notebook with a pen.
9. responde — Lucía raises her hand in a classroom to answer.

## Лист 3 — вещи (тема 5)

Порядок: `libro cuaderno boligrafo mochila llave mesa silla ordenador movil`

Здесь без людей: каждая ячейка — один предмет крупно.

1. el libro — a closed hardcover book.
2. el cuaderno — a spiral notebook.
3. el bolígrafo — a ballpoint pen.
4. la mochila — a school backpack.
5. la llave — a single door key.
6. la mesa — a wooden table.
7. la silla — a wooden chair.
8. el ordenador — a laptop computer, open.
9. el móvil — a smartphone.

## Лист 4 — профессии (тема 6)

Порядок: `profesor medico estudiante camarero ingeniero programador hospital escuela oficina`

Профессия — человек за работой, по пояс. Персонажи: Profesora — woman about 45, dark hair with grey streaks in a bun,
round glasses, grey cardigan. Médica — woman about 40, dark hair tied back, white coat, stethoscope.
Camarero — man about 40, short black hair, white shirt, black waistcoat and bow tie.

1. el profesor / la profesora — the teacher (Profesora) stands at a whiteboard with a pointer, the board shows only simple shapes.
2. el médico / la médica — the doctor (Médica) with a stethoscope and a clipboard.
3. el/la estudiante — Lucía with a backpack and books in front of a university building.
4. el camarero / la camarera — the waiter (Camarero) carries a tray with two coffee cups.
5. el ingeniero / la ingeniera — a woman in a white hard hat and safety vest holding a rolled blueprint.
6. el programador / la programadora — Pablo types on a laptop, simple coloured lines of code on the screen, no readable letters.
7. el hospital — a small white hospital building with a red cross.
8. la escuela — a small school building with a clock above the door.
9. la oficina — an office desk with a computer monitor, a plant and a mug.
