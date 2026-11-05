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
