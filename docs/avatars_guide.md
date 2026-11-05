# Аватары персонажей диалогов (сайт, A0–A1)

У каждого персонажа диалогов один аватар во всех уроках. Он хранится в файле `content/art/avatars/<slug>.webp`
(128×128, нарезан из листа ChatGPT). Персонаж, его голос и slug аватара записаны в `CAST` в `espanol/site_audio.py`.
Если файла нет, сайт показывает нейтральную иконку человека в цвете собеседника.

## Как добавить

1. Сгенерировать лист в ChatGPT по промпту ниже. Стиль — тот же, что у картинок слов: плоская векторная
   иллюстрация в тёплых пастельных цветах.
2. Нарезать лист:

   ```bash
   python tools/art/slice_avatars.py лист1.png 3x3 lucia pablo ana diego elena profesora ivan olga irina
   ```

   Персонажи перечисляются слева направо, сверху вниз — в том же порядке, что в промпте.
3. Собрать сайт и посмотреть диалог. Персонаж, которого ещё нет в `CAST`, нужно туда дописать:
   имя, пол, голос и slug.

## Общий стиль (в начало каждого промпта)

> Flat vector illustration, warm pastel colours, soft rounded shapes, simple friendly faces, no outlines heavier
> than 2 px, same style for every character. A square image divided into a 3×3 grid of equal square cells separated
> by thin white gaps. In each cell: a head-and-shoulders portrait of one adult person facing the viewer, centred,
> face filling about 60 % of the cell, on a plain soft pastel background of its own colour. No text, no letters,
> no frames, no props outside the cell.

## Лист 1 (3×3)

Порядок: `lucia pablo ana diego elena profesora ivan olga irina`

1. Lucía — Spanish woman, about 25, long dark-brown wavy hair, warm smile, mustard sweater.
2. Pablo — Spanish man, about 27, short dark hair, short neat beard, light-blue shirt.
3. Ana — woman, about 28, auburn hair in a high ponytail, green top.
4. Diego — man, about 30, curly black hair, round glasses, orange T-shirt.
5. Elena — woman, about 35, short black bob, small red earrings, teal blouse.
6. Profesora — teacher, woman about 45, dark hair with grey streaks in a bun, round glasses, grey cardigan.
7. Iván — young man, about 22, short light-blond hair, navy hoodie.
8. Olga — young woman, about 23, straight light-brown hair with a fringe, lilac sweater.
9. Irina — woman, about 30, blonde hair in a side braid, beige coat.

## Лист 2 (3×3)

Порядок: `karina carlos senor_garcia recepcionista camarero dependienta clara medica sergio`

1. Karina — woman, about 26, shoulder-length red hair, freckles, yellow top.
2. Carlos — man, about 35, neat side-parted brown hair, navy blazer over a white shirt.
3. Señor García — elderly man, about 70, white hair and white moustache, brown flat cap, brown jacket.
4. Recepcionista — receptionist, woman about 35, hair in a neat bun, small headset microphone, white blouse with a name badge.
5. Camarero — waiter, man about 40, short black hair, white shirt, black waistcoat and bow tie.
6. Dependienta — shop assistant, woman about 30, dark curly hair, shop apron with a name badge.
7. Clara — young woman, about 24, short pink-dyed hair, denim jacket.
8. Médica — doctor, woman about 40, dark hair tied back, white coat, stethoscope around the neck.
9. Sergio — man, about 30, messy brown hair, wool scarf, slightly tired face (he has a cold).

## Лист 3 (2×2, в промпте «2×2 grid» вместо «3×3 grid»)

Порядок: `madre senora tom hugo`

1. Madre — mother, woman about 50, chin-length dark hair, warm cardigan.
2. Señora — elderly lady, about 65, short grey curly hair, pearl necklace.
3. Tom — English tourist, man about 25, ginger hair, light-blue cap, backpack straps.
4. Hugo — man, about 28, very short buzz-cut hair, green jacket.
