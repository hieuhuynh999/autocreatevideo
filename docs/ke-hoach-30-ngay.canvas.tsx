import {
  Button,
  Callout,
  H1,
  H2,
  H3,
  Row,
  Select,
  Stack,
  Stat,
  Table,
  Text,
  TextArea,
  useCanvasState,
} from "cursor/canvas";

const LOCK =
  "3D animated, not a photograph. The same girl Na, age 5, round face, short black hair, pink dress, white shoes, fully clothed. The same cream rabbit Bong, long ears, blue scarf. Toy house, white fence, flowers. No text.";

type Scene = [string, string];
type Clip = {
  title: string;
  theme: string;
  overview: string;
  music: string;
  scenes: Scene[];
};
type DayPlan = { format: string; from: string; clips: [Clip, Clip] };

function clip(
  title: string,
  theme: string,
  overview: string,
  music: string,
  scenes: Scene[],
): Clip {
  return { title, theme, overview, music, scenes };
}

const DAYS: DayPlan[] = [
  {
    format: "Đoán xem tôi là gì",
    from: "Câu đố What am I trên YouTube Shorts",
    clips: [
      clip("What am I? Apple", "Đoán quả táo", "Na giấu quả táo, rồi mới cho xem.", "Tắt", [
        ["Na giấu quả táo đỏ sau lưng, nghiêng đầu nhìn người xem, vườn nhà đồ chơi", "What am I? — Tôi là gì"],
        ["Bông thò đầu sau chậu hoa, tai dựng, nhìn quanh", "Can you guess? — Bạn đoán không"],
        ["Na đưa nửa quả táo đỏ ra phía trước", "Look! — Nhìn này"],
        ["Bông chỉ vào quả táo đỏ và mỉm cười", "An apple! — Một quả táo"],
        ["Na đưa quả táo về phía camera, Bông vỗ tay bên cạnh", "Say apple! — Hãy nói apple"],
        ["Hai bạn giơ quả táo và vẫy tay, Bông lùi về cửa nhà đồ chơi", "Yummy! — Ngon quá"],
      ]),
      clip("What am I? Sun", "Đoán mặt trời", "Hai bạn ngước nhìn nắng rồi gọi tên.", "Tắt", [
        ["Na che mắt nhìn lên trời xanh phía trên hàng rào trắng", "What am I? — Tôi là gì"],
        ["Bông ngước nhìn vệt nắng trên lối đá", "Can you guess? — Bạn đoán không"],
        ["Na chỉ lên khoảng nắng ấm", "Look! — Nhìn này"],
        ["Bông nheo mắt vui dưới nắng, khăn xanh lay nhẹ", "The sun! — Mặt trời"],
        ["Na dang hai tay đón nắng, Bông đứng cạnh", "Say sun! — Hãy nói sun"],
        ["Hai bạn vẫy tay trong nắng, Bông về phía cửa", "Warm! — Ấm quá"],
      ]),
    ],
  },
  {
    format: "Từ trái nghĩa",
    from: "Opposite words diễn bằng hành động",
    clips: [
      clip("Up and down", "Lên và xuống", "Na và Bông đưa tay lên rồi hạ xuống.", "Thiếu nhi", [
        ["Na đứng trên bậc thềm nhà đồ chơi, hai tay giơ cao", "Up! — Lên"],
        ["Bông ngồi thấp cạnh chậu hoa, hai tai cụp nhẹ", "Down! — Xuống"],
        ["Na nhón chân với một bông hoa cao", "Up, up! — Lên, lên"],
        ["Bông cúi nhặt một cánh hoa dưới đất", "Down, down! — Xuống, xuống"],
        ["Na giơ tay lên, Bông hạ tay xuống, cùng nhìn camera", "Up and down! — Lên và xuống"],
        ["Hai bạn đứng thẳng và vẫy tạm biệt", "Goodbye! — Tạm biệt"],
      ]),
      clip("Open and close", "Mở và đóng", "Cửa nhà đồ chơi mở rồi khép.", "Thiếu nhi", [
        ["Na đẩy cửa nhà đồ chơi mở rộng", "Open! — Mở"],
        ["Bông kéo cửa khép lại, chỉ còn khe sáng", "Close! — Đóng"],
        ["Na mở cửa lần nữa và bước một chân ra", "Open, please! — Mở ra nào"],
        ["Bông khép cửa nhẹ, vẫn mỉm cười", "Close, please! — Đóng lại nào"],
        ["Cửa mở, hai bạn đứng trong khung cửa nhìn camera", "Open and close! — Mở và đóng"],
        ["Hai bạn khép cửa sau lưng và vẫy từ ngoài sân", "Bye! — Tạm biệt"],
      ]),
    ],
  },
  {
    format: "Làm theo tôi",
    from: "Repeat after me, bạn nhỏ bắt chước",
    clips: [
      clip("Copy the wave", "Vẫy tay theo", "Na vẫy, Bông vẫy, rồi mời người xem.", "Thiếu nhi", [
        ["Na vẫy một tay chậm, nhìn đúng vào camera", "Wave! — Vẫy tay"],
        ["Bông vẫy một chân trước y như Na", "Wave! — Vẫy tay"],
        ["Na vẫy hai tay cùng lúc", "Wave, wave! — Vẫy, vẫy"],
        ["Bông vẫy hai chân trước, tai nhún", "I can wave! — Mình vẫy được"],
        ["Na đưa bàn tay mở về camera, Bông đứng cạnh", "Your turn! — Đến lượt bạn"],
        ["Hai bạn vẫy lần cuối rồi lùi về cửa", "Bye, bye! — Tạm biệt"],
      ]),
      clip("Copy the jump", "Nhảy theo", "Nhảy một nhịp nhỏ trong vườn.", "Thiếu nhi", [
        ["Na nhảy một nhịp trên lối đá, váy hồng bay nhẹ", "Jump! — Nhảy"],
        ["Bông nhảy một nhịp cạnh hàng rào", "Jump! — Nhảy"],
        ["Na nhảy rồi đáp xuống hai chân", "Jump again! — Nhảy nữa"],
        ["Bông nhảy và mỉm cười khi chạm đất", "I can jump! — Mình nhảy được"],
        ["Na chỉ xuống đất mời người xem nhảy tại chỗ, Bông chờ", "Your turn! — Đến lượt bạn"],
        ["Hai bạn cúi chào nhỏ rồi vẫy", "Goodbye! — Tạm biệt"],
      ]),
    ],
  },
  {
    format: "Tìm trong vườn",
    from: "Tìm đồ, khán giả được mời nhìn theo",
    clips: [
      clip("Where is the ball?", "Tìm quả bóng", "Quả bóng đỏ trốn sau hàng rào.", "Tắt", [
        ["Na nhìn quanh vườn, hai tay xoay nhẹ", "Where is it? — Nó ở đâu"],
        ["Bông nhìn sau chậu hoa, chưa thấy", "Not here! — Không ở đây"],
        ["Na cúi nhìn dưới bụi hoa tím", "Look there! — Nhìn đằng kia"],
        ["Bông kéo một quả bóng đỏ từ sau hàng rào ra", "A ball! — Một quả bóng"],
        ["Na lăn bóng chậm về phía camera", "Say ball! — Hãy nói ball"],
        ["Hai bạn ôm bóng và vẫy", "We found it! — Mình tìm thấy rồi"],
      ]),
      clip("Where is the flower?", "Tìm bông hoa", "Một bông hoa vàng nằm trên bậc thềm.", "Tắt", [
        ["Bông hếch mũi ngửi quanh lối đi", "Where is it? — Nó ở đâu"],
        ["Na nhìn lên mái nhà đồ chơi", "Not here! — Không ở đây"],
        ["Bông chỉ xuống bậc thềm", "Look there! — Nhìn đằng kia"],
        ["Na nhặt một bông hoa vàng trên bậc", "A flower! — Một bông hoa"],
        ["Na giơ hoa vàng lên, Bông đứng cạnh", "Say flower! — Hãy nói flower"],
        ["Hai bạn cắm hoa vào chậu và vẫy", "Pretty! — Đẹp quá"],
      ]),
    ],
  },
  {
    format: "Cái này hay cái kia",
    from: "This or that, người xem chọn",
    clips: [
      clip("Red or blue?", "Đỏ hay xanh", "Hai bông hoa, người xem được hỏi trước.", "Tắt", [
        ["Na cầm hoa đỏ một tay, hoa xanh một tay", "Red or blue? — Đỏ hay xanh"],
        ["Bông nghiêng đầu nhìn hai bông hoa", "Which one? — Cái nào"],
        ["Na đưa hoa đỏ lên cao hơn", "Red! — Đỏ"],
        ["Bông ôm hoa xanh vào ngực", "Blue! — Xanh"],
        ["Hai bạn giơ đúng hoa của mình về phía camera", "Red and blue! — Đỏ và xanh"],
        ["Hai bạn trao hoa cho nhau và vẫy", "Your pick! — Bạn chọn đi"],
      ]),
      clip("Big or small?", "To hay nhỏ", "Hai quả bóng cạnh nhau.", "Tắt", [
        ["Na đứng giữa quả bóng to và quả bóng nhỏ", "Big or small? — To hay nhỏ"],
        ["Bông so hai chân trước với quả bóng nhỏ", "Which one? — Cái nào"],
        ["Na ôm quả bóng to, bóng gần bằng người", "Big! — To"],
        ["Bông bê quả bóng nhỏ trên một chân", "Small! — Nhỏ"],
        ["Hai quả bóng nằm cạnh nhau, hai bạn chỉ", "Big and small! — To và nhỏ"],
        ["Hai bạn ngồi xuống cạnh bóng và vẫy", "You choose! — Bạn chọn"],
      ]),
    ],
  },
  {
    format: "Đếm cùng nhau",
    from: "Đếm vật thật trong một cảnh",
    clips: [
      clip("Count the flowers", "Đếm hoa", "Một, hai, rồi ba bông trên hàng rào.", "Thiếu nhi", [
        ["Na chỉ một bông hoa hồng trên hàng rào", "One! — Một"],
        ["Bông chỉ thêm bông hoa vàng bên cạnh", "Two! — Hai"],
        ["Na chỉ nốt bông hoa tím", "Three! — Ba"],
        ["Ba bông hoa cùng trong khung, hai bạn đứng trước", "One, two, three! — Một, hai, ba"],
        ["Na giơ ba ngón tay, Bông gật", "Say three! — Hãy nói three"],
        ["Hai bạn cúi chào ba bông hoa rồi vẫy", "Good job! — Giỏi lắm"],
      ]),
      clip("Count the steps", "Đếm bước", "Ba bước từ cổng đến cửa.", "Thiếu nhi", [
        ["Na bước một bước trên lối đá", "One! — Một"],
        ["Bông bước thêm một bước", "Two! — Hai"],
        ["Na bước bước thứ ba tới cửa", "Three! — Ba"],
        ["Hai bạn đứng trên bậc cuối và nhìn lại lối đi", "One, two, three! — Một, hai, ba"],
        ["Na vỗ ba cái chậm, Bông đếm theo bằng tai nhún", "Say three! — Hãy nói three"],
        ["Hai bạn bước trở ra cổng và vẫy", "Bye! — Tạm biệt"],
      ]),
    ],
  },
  {
    format: "Chuyện mất đồ",
    from: "Một chuyện ngắn có mất và tìm thấy",
    clips: [
      clip("Bông's scarf", "Khăn của Bông", "Khăn xanh lạc trên hàng rào rồi được trả.", "Tắt", [
        ["Bông sờ cổ, không thấy khăn xanh", "Oh no! — Ôi không"],
        ["Na nhìn quanh bụi hoa", "Where is it? — Nó ở đâu"],
        ["Na trông thấy khăn xanh vắt trên hàng rào", "I see it! — Mình thấy rồi"],
        ["Na đưa khăn cho Bông", "Here you are! — Của bạn đây"],
        ["Bông quàng lại khăn và cúi cảm ơn", "Thank you! — Cảm ơn"],
        ["Hai bạn đi cạnh nhau về cửa, vẫy", "Friends! — Bạn bè"],
      ]),
      clip("Na's shoe", "Giày của Na", "Một chiếc giày trắng nằm dưới ghế gỗ.", "Tắt", [
        ["Na nhìn xuống, một chân chỉ có tất", "Oh no! — Ôi không"],
        ["Bông nhìn dưới chậu hoa", "Where is it? — Nó ở đâu"],
        ["Bông kéo một giày trắng từ dưới ghế nhỏ", "I see it! — Mình thấy rồi"],
        ["Bông đặt giày trước Na", "Here you are! — Của bạn đây"],
        ["Na xỏ giày và cúi cảm ơn", "Thank you! — Cảm ơn"],
        ["Hai bạn cùng đi một vòng ngắn rồi vẫy", "Let's go! — Mình đi nào"],
      ]),
    ],
  },
  {
    format: "Chờ đến cuối",
    from: "Wait for it, điều hay hiện ở cảnh cuối",
    clips: [
      clip("The bud opens", "Nụ hoa nở", "Nụ khép, rồi mở thành hoa.", "Tắt", [
        ["Na và Bông nhìn một nụ hoa còn khép trên bụi", "Wait! — Chờ đã"],
        ["Nụ nhích mở một chút, hai bạn cúi sát", "Look! — Nhìn này"],
        ["Na thì thầm, ngón tay để gần nụ, không chạm", "Almost! — Sắp rồi"],
        ["Hoa vàng mở hết, ánh nắng trên cánh", "Wow! — Ồ"],
        ["Bông chỉ vào hoa đang nở", "A flower! — Một bông hoa"],
        ["Hai bạn lùi lại để hoa ở giữa khung và vẫy", "So pretty! — Đẹp quá"],
      ]),
      clip("The door opens", "Cửa mở", "Cửa khép, rồi Na xuất hiện.", "Tắt", [
        ["Cửa nhà đồ chơi khép, Bông ngồi chờ ngoài sân", "Wait! — Chờ đã"],
        ["Cửa nhích một khe sáng", "Look! — Nhìn này"],
        ["Bông nghiêng tai về phía cửa", "Almost! — Sắp rồi"],
        ["Na mở cửa và cười", "Hello! — Xin chào"],
        ["Na bước ra, Bông nhảy một nhịp nhỏ", "It's Na! — Là Na"],
        ["Hai bạn cùng đứng trước cửa mở và vẫy", "Surprise! — Bất ngờ"],
      ]),
    ],
  },
  {
    format: "Mặt cảm xúc",
    from: "Một cảm xúc rõ trên mặt, rồi bạn kia đáp lại",
    clips: [
      clip("Happy", "Vui", "Niềm vui lan từ Na sang Bông.", "Thiếu nhi", [
        ["Na cười rộng, hai tay ôm một bó hoa nhỏ", "Happy! — Vui"],
        ["Bông nhìn Na, tai dựng", "Are you happy? — Bạn vui không"],
        ["Na gật và nhảy một nhịp", "Yes, I am! — Có, mình vui"],
        ["Bông cười theo, khăn xanh bay", "Me too! — Mình cũng vậy"],
        ["Hai bạn cười nhìn camera", "Say happy! — Hãy nói happy"],
        ["Hai bạn ôm một cái thật ngắn rồi vẫy", "Happy friends! — Bạn vui"],
      ]),
      clip("Brave", "Mạnh dạn", "Bông ngại cửa tối, Na đứng cạnh, rồi Bông bước.", "Tắt", [
        ["Bông đứng trước cửa hơi khép, tai cụp một chút", "Oh! — Ồ"],
        ["Na đứng sát bên, không kéo", "I am here! — Mình ở đây"],
        ["Bông thở một hơi và đặt chân lên bậc", "I am brave! — Mình dám"],
        ["Bông bước qua cửa, Na mỉm cười", "Good! — Tốt lắm"],
        ["Hai bạn đứng trong cửa sáng nhìn camera", "Say brave! — Hãy nói brave"],
        ["Hai bạn vẫy từ ngưỡng cửa", "You can! — Bạn làm được"],
      ]),
    ],
  },
  {
    format: "Cửa hàng lịch sự",
    from: "Đóng vai mua bán, lời please và thank you",
    clips: [
      clip("Please", "Làm ơn", "Na xin một bông hoa ở quầy gỗ nhỏ.", "Tắt", [
        ["Bông đứng sau quầy gỗ nhỏ, hoa vàng trên mặt quầy", "Hello! — Xin chào"],
        ["Na chỉ bông hoa, tay chưa lấy", "Please! — Làm ơn"],
        ["Bông gật và đẩy hoa về phía Na", "Here you go! — Của bạn đây"],
        ["Na nhận hoa bằng hai tay", "Thank you! — Cảm ơn"],
        ["Na giơ hoa, nhìn camera", "Say please! — Hãy nói please"],
        ["Hai bạn cúi chào qua quầy rồi vẫy", "Bye! — Tạm biệt"],
      ]),
      clip("Thank you", "Cảm ơn", "Bông xin quả táo, Na đưa.", "Tắt", [
        ["Na ngồi sau quầy, một quả táo đỏ trên khay", "Hello! — Xin chào"],
        ["Bông chỉ quả táo", "Please! — Làm ơn"],
        ["Na đặt táo vào chân Bông", "Here you go! — Của bạn đây"],
        ["Bông ôm táo và cúi đầu", "Thank you! — Cảm ơn"],
        ["Bông nhìn camera, táo còn trong chân", "Say thank you! — Hãy nói thank you"],
        ["Na khoát tay mời Bông đi chơi, cả hai vẫy", "Let's play! — Mình chơi nào"],
      ]),
    ],
  },
  {
    format: "Đi theo người dẫn",
    from: "Follow the leader quanh vườn",
    clips: [
      clip("Follow Na", "Đi theo Na", "Bông bước đúng lối Na đã đi.", "Thiếu nhi", [
        ["Na chỉ lối đá và bước trước", "Follow me! — Đi theo mình"],
        ["Bông bước đúng vào dấu chân Na", "I follow! — Mình đi theo"],
        ["Na vòng qua chậu hoa", "This way! — Đường này"],
        ["Bông vòng theo, khăn xanh kéo nhẹ", "This way! — Đường này"],
        ["Hai bạn dừng ở cửa và nhìn camera", "Your turn! — Đến lượt bạn"],
        ["Na dẫn Bông thêm một bước rồi cả hai vẫy", "Goodbye! — Tạm biệt"],
      ]),
      clip("Follow Bông", "Đi theo Bông", "Na đi theo Bông quanh hàng rào.", "Thiếu nhi", [
        ["Bông nhảy một bước dọc hàng rào", "Follow me! — Đi theo mình"],
        ["Na bước theo, tay để sau lưng", "I follow! — Mình đi theo"],
        ["Bông dừng ở cổng gỗ", "Stop here! — Dừng ở đây"],
        ["Na dừng đúng cạnh Bông", "I stop! — Mình dừng"],
        ["Bông chỉ camera mời người xem bước tại chỗ", "Your turn! — Đến lượt bạn"],
        ["Hai bạn cúi chào ở cổng", "Bye! — Tạm biệt"],
      ]),
    ],
  },
  {
    format: "Nắng và mưa",
    from: "Một trời, một hoạt động, không mưa bão",
    clips: [
      clip("Sunny day", "Ngày nắng", "Đội mũ và tưới hoa dưới nắng.", "Thiếu nhi", [
        ["Na đội mũ rơm, nắng trên lối đá", "Sunny! — Nắng"],
        ["Bông nheo mắt, khăn xanh sáng hơn", "It is sunny! — Trời nắng"],
        ["Na tưới một dòng nước nhỏ lên hoa", "Water the flowers! — Tưới hoa"],
        ["Bông hứng một giọt trên chân và cười", "Cool! — Mát quá"],
        ["Hai bạn đứng dưới nắng nhìn camera", "Say sunny! — Hãy nói sunny"],
        ["Hai bạn cất bình tưới và vẫy", "See you! — Hẹn gặp lại"],
      ]),
      clip("Gentle rain", "Mưa nhẹ", "Mưa nhỏ, hai bạn đứng dưới mái hiên.", "Thiếu nhi", [
        ["Những giọt mưa nhỏ trên lá, Na nhìn từ hiên nhà", "Rain! — Mưa"],
        ["Bông thò một chân ra ngoài hiên rồi rụt lại", "It is raining! — Trời đang mưa"],
        ["Na mở một chiếc ô nhỏ màu vàng", "Umbrella! — Cái ô"],
        ["Hai bạn đứng chung dưới ô, mưa phía sau", "We are dry! — Mình không ướt"],
        ["Na chỉ những giọt trên lá", "Say rain! — Hãy nói rain"],
        ["Mưa ngớt, hai bạn đóng ô và vẫy", "All done! — Xong rồi"],
      ]),
    ],
  },
  {
    format: "Đi dã ngoại",
    from: "Một chuyện đi chơi có đầu và kết",
    clips: [
      clip("Pack the basket", "Xếp giỏ", "Xếp táo và khăn vào giỏ rồi ra vườn.", "Thiếu nhi", [
        ["Na mở một giỏ mây trên bậc thềm", "Picnic! — Đi dã ngoại"],
        ["Bông bỏ một quả táo vào giỏ", "Apple in! — Táo vào"],
        ["Na gấp một khăn kẻ ô nhỏ lên trên", "Cloth in! — Khăn vào"],
        ["Hai bạn khiêng giỏ ra thảm cỏ", "Let's go! — Mình đi nào"],
        ["Giỏ mở, hoa xung quanh, hai bạn ngồi", "Yummy picnic! — Bữa ngon"],
        ["Hai bạn đậy giỏ và vẫy trên thảm", "Bye! — Tạm biệt"],
      ]),
      clip("Share the snack", "Chia món", "Một quả táo được bẻ làm đôi.", "Thiếu nhi", [
        ["Na cầm một quả táo trên thảm cỏ", "One apple! — Một quả táo"],
        ["Bông nhìn táo, chưa lấy", "For me? — Cho mình à"],
        ["Na bẻ táo làm hai, đưa một nửa", "Share! — Chia nào"],
        ["Bông nhận nửa táo và gật", "Thank you! — Cảm ơn"],
        ["Hai bạn ngồi cạnh nhau, mỗi bạn một nửa", "We share! — Mình chia"],
        ["Hai bạn dựng giỏ và vẫy", "Good friends! — Bạn tốt"],
      ]),
    ],
  },
  {
    format: "Làm nhầm rồi sửa",
    from: "Hài nhẹ, tự sửa, không chế giễu",
    clips: [
      clip("Shoe mix-up", "Xỏ nhầm giày", "Na xỏ giày vào tay, rồi sửa.", "Thiếu nhi", [
        ["Na cười, một chiếc giày trắng nằm trên bàn tay", "Oops! — Ối"],
        ["Bông nghiêng đầu nhìn giày trên tay Na", "On your hand? — Trên tay à"],
        ["Na lắc đầu và bỏ giày xuống đất", "No, no! — Không, không"],
        ["Na xỏ giày vào chân phải", "On my foot! — Vào chân"],
        ["Bông chỉ xuống chân Na và gật", "That's right! — Đúng rồi"],
        ["Hai bạn đi ba bước đúng giày rồi vẫy", "Goodbye! — Tạm biệt"],
      ]),
      clip("Scarf mix-up", "Quàng nhầm khăn", "Bông đội khăn lên đầu, rồi quàng lại cổ.", "Thiếu nhi", [
        ["Bông đội khăn xanh trên đầu như mũ", "Oops! — Ối"],
        ["Na chỉ cổ của mình", "On your neck! — Vào cổ"],
        ["Bông kéo khăn xuống", "Like this? — Như này à"],
        ["Na giúp Bông quàng khăn quanh cổ", "Yes! — Đúng"],
        ["Bông vuốt khăn và nhìn camera", "My scarf! — Khăn của mình"],
        ["Hai bạn cúi chào, khăn đã đúng chỗ", "All better! — Ổn rồi"],
      ]),
    ],
  },
  {
    format: "Hỏi bạn nhỏ",
    from: "Câu hỏi thẳng vào camera, rồi làm mẫu",
    clips: [
      clip("Can you clap?", "Bạn vỗ tay không", "Hỏi trước, vỗ sau.", "Thiếu nhi", [
        ["Na nhìn thẳng camera, hai tay chưa chạm", "Can you clap? — Bạn vỗ tay không"],
        ["Bông chờ, tai dựng", "Ready? — Sẵn sàng chưa"],
        ["Na vỗ một cái rõ", "Clap! — Vỗ"],
        ["Bông vỗ hai chân trước vào nhau", "Clap, clap! — Vỗ, vỗ"],
        ["Na giơ hai tay chờ người xem vỗ", "Your turn! — Đến lượt bạn"],
        ["Hai bạn vỗ lần cuối rồi vẫy", "Yay! — Hoan hô"],
      ]),
      clip("Can you spin?", "Bạn xoay không", "Xoay một vòng chậm trong vườn.", "Thiếu nhi", [
        ["Na đứng giữa lối đá, chưa xoay", "Can you spin? — Bạn xoay không"],
        ["Bông nhìn Na", "Ready? — Sẵn sàng chưa"],
        ["Na xoay một vòng chậm, váy hồng xòe", "Spin! — Xoay"],
        ["Bông xoay một vòng, khăn bay", "Spin, spin! — Xoay, xoay"],
        ["Hai bạn dừng, nhìn camera", "Your turn! — Đến lượt bạn"],
        ["Hai bạn hơi chóng mặt vui và vẫy", "Wow! — Ồ"],
      ]),
    ],
  },
  {
    format: "Nghe tiếng rồi nói chữ",
    from: "Một tiếng ngắn, rồi từ tiếng Anh",
    clips: [
      clip("Tweet, bird", "Tiếng chim", "Chim trên hàng rào, không chữ trong hình.", "Tắt", [
        ["Một chú chim nhỏ đậu trên hàng rào, Na lắng nghe", "Tweet! — Chíp"],
        ["Bông nghiêng tai về phía chim", "What is that? — Đó là gì"],
        ["Chim vỗ cánh một cái, vẫn trên hàng rào", "Tweet, tweet! — Chíp, chíp"],
        ["Na chỉ chim và mỉm cười", "A bird! — Một con chim"],
        ["Bông chỉ chim, Na gật", "Say bird! — Hãy nói bird"],
        ["Chim bay xa trong khung, hai bạn vẫy theo", "Bye, bird! — Tạm biệt chim"],
      ]),
      clip("Drip, water", "Tiếng nước", "Giọt nước từ bình tưới.", "Tắt", [
        ["Một giọt nước rơi từ vòi bình, Na nhìn", "Drip! — Tách"],
        ["Bông nhìn vũng nhỏ trên đá", "What is that? — Đó là gì"],
        ["Na nghiêng bình, thêm một giọt", "Drip, drip! — Tách, tách"],
        ["Bông chạm nhẹ vũng nước", "Water! — Nước"],
        ["Na giơ bình tưới về phía hoa", "Say water! — Hãy nói water"],
        ["Hai bạn đặt bình xuống và vẫy", "All done! — Xong rồi"],
      ]),
    ],
  },
  {
    format: "To và nhỏ",
    from: "So hai vật cùng loại",
    clips: [
      clip("Two flowers", "Hai bông hoa", "Hoa to và hoa nhỏ trên cùng một bụi.", "Thiếu nhi", [
        ["Na đứng cạnh một bông hoa rất to", "Big! — To"],
        ["Bông cúi xuống một bông hoa rất nhỏ", "Small! — Nhỏ"],
        ["Na dang tay bằng bề ngang hoa to", "So big! — To quá"],
        ["Bông kẹp hoa nhỏ giữa hai chân", "So small! — Nhỏ quá"],
        ["Hai bông hoa cạnh nhau, hai bạn chỉ", "Big and small! — To và nhỏ"],
        ["Hai bạn không hái hoa, chỉ vẫy và lùi", "Bye, flowers! — Tạm biệt các hoa"],
      ]),
      clip("Two balls", "Hai quả bóng", "Bóng to cho cả hai, bóng nhỏ cho Bông.", "Thiếu nhi", [
        ["Na đẩy quả bóng to bằng người", "Big ball! — Bóng to"],
        ["Bông ôm quả bóng nhỏ", "Small ball! — Bóng nhỏ"],
        ["Na ngồi lên bóng to như ghế, chân chạm đất", "So big! — To quá"],
        ["Bông giấu bóng nhỏ sau tai", "So small! — Nhỏ quá"],
        ["Hai bóng nằm giữa, hai bạn nhìn camera", "Big and small! — To và nhỏ"],
        ["Hai bạn lăn bóng về nhà và vẫy", "Play again! — Chơi nữa nhé"],
      ]),
    ],
  },
  {
    format: "Buổi sáng",
    from: "Một chuỗi việc sáng, không lặp một từ",
    clips: [
      clip("Na's morning", "Sáng của Na", "Dậy, vươn, rửa, đi giày, chào, chơi.", "Thiếu nhi", [
        ["Na bước ra cửa nhà đồ chơi, dụi mắt cười", "Good morning! — Chào buổi sáng"],
        ["Na vươn hai tay lên trời", "Stretch! — Vươn vai"],
        ["Na rửa tay ở chậu nước nhỏ ngoài sân", "Wash! — Rửa"],
        ["Na xỏ hai giày trắng", "Shoes on! — Đi giày"],
        ["Na vẫy Bông đang ở hàng rào", "Hello, Bông! — Chào Bông"],
        ["Hai bạn chạy chậm ra vườn", "Let's play! — Mình chơi nào"],
      ]),
      clip("Bông's morning", "Sáng của Bông", "Bông dậy theo một chuỗi khác.", "Thiếu nhi", [
        ["Bông thò đầu từ cửa, nắng trên tai", "Good morning! — Chào buổi sáng"],
        ["Bông rùng mình một cái cho khăn thẳng", "Shake! — Rung"],
        ["Bông uống một ngụm nước từ bát nhỏ", "Drink! — Uống"],
        ["Bông chỉnh khăn xanh cho ngay", "Scarf on! — Quàng khăn"],
        ["Bông vẫy Na ở bậc thềm", "Hello, Na! — Chào Na"],
        ["Hai bạn đi về phía hoa", "Let's go! — Mình đi nào"],
      ]),
    ],
  },
  {
    format: "Giúp một tay",
    from: "Việc khó khi một mình, dễ khi có hai",
    clips: [
      clip("Heavy basket", "Giỏ nặng", "Giỏ hoa nặng, hai bạn khiêng.", "Tắt", [
        ["Na kéo giỏ mây, giỏ chỉ nhích", "Too heavy! — Nặng quá"],
        ["Bông chạy lại", "I can help! — Mình giúp được"],
        ["Mỗi bạn một quai giỏ", "Together! — Cùng nhau"],
        ["Giỏ được đặt dưới gốc hoa", "We did it! — Mình làm được"],
        ["Na lau trán cười, Bông gật", "Thank you! — Cảm ơn"],
        ["Hai bạn ngồi nghỉ cạnh giỏ và vẫy", "Team! — Một đội"],
      ]),
      clip("High flower", "Hoa trên cao", "Na với không tới, Bông đứng nhìn, rồi Na nhón an toàn trên bậc.", "Tắt", [
        ["Na với một bông hoa cao hơn tay", "Too high! — Cao quá"],
        ["Bông nhìn lên", "I can help! — Mình giúp được"],
        ["Na đứng trên bậc thấp, Bông giữ mép váy cho vững", "Careful! — Cẩn thận"],
        ["Na chạm được cành, không bẻ gãy, chỉ ngửi", "I reached it! — Mình với tới"],
        ["Na bước xuống, Bông buông váy", "Thank you! — Cảm ơn"],
        ["Hai bạn để hoa ở trên cây và vẫy", "Leave it! — Để hoa ở đó"],
      ]),
    ],
  },
  {
    format: "Săn một màu",
    from: "Một màu, nhiều chỗ trong vườn",
    clips: [
      clip("Red hunt", "Săn màu đỏ", "Đỏ ở hoa, táo, và bóng.", "Thiếu nhi", [
        ["Na chỉ một cánh hoa đỏ", "Red! — Đỏ"],
        ["Bông lăn quả táo đỏ ra", "Red apple! — Táo đỏ"],
        ["Na tìm thấy quả bóng đỏ sau chậu", "Red ball! — Bóng đỏ"],
        ["Ba đồ đỏ xếp hàng trên đá", "So much red! — Nhiều màu đỏ"],
        ["Hai bạn chỉ hàng đồ đỏ", "Say red! — Hãy nói red"],
        ["Hai bạn xếp đồ lại chỗ cũ và vẫy", "Bye! — Tạm biệt"],
      ]),
      clip("Yellow hunt", "Săn màu vàng", "Vàng ở hoa, nắng, và ô.", "Thiếu nhi", [
        ["Bông chỉ hoa vàng", "Yellow! — Vàng"],
        ["Na chỉ vệt nắng trên lối", "Yellow sun! — Nắng vàng"],
        ["Bông kéo một chiếc ô vàng từ hiên", "Yellow umbrella! — Ô vàng"],
        ["Hoa, nắng và ô cùng trong khung", "So much yellow! — Nhiều màu vàng"],
        ["Hai bạn nhìn camera", "Say yellow! — Hãy nói yellow"],
        ["Hai bạn cất ô và vẫy", "All done! — Xong rồi"],
      ]),
    ],
  },
  {
    format: "Chậm rồi nhanh",
    from: "Cùng một việc, hai tốc độ",
    clips: [
      clip("Slow walk, quick walk", "Đi chậm, đi nhanh", "Một vòng hàng rào hai kiểu.", "Thiếu nhi", [
        ["Na đi rất chậm dọc hàng rào, tay buông", "Slow! — Chậm"],
        ["Bông đi chậm theo, từng bước rõ", "Slow, slow! — Chậm, chậm"],
        ["Na đi những bước ngắn nhanh hơn, vẫn an toàn", "Quick! — Nhanh"],
        ["Bông đi nhanh theo, tai dựng", "Quick, quick! — Nhanh, nhanh"],
        ["Hai bạn dừng ở cổng", "Slow and quick! — Chậm và nhanh"],
        ["Hai bạn thở cười và vẫy", "Stop! — Dừng"],
      ]),
      clip("Slow clap, quick clap", "Vỗ chậm, vỗ nhanh", "Nhịp tay đổi tốc độ.", "Thiếu nhi", [
        ["Na vỗ một cái, giữ tay", "Slow! — Chậm"],
        ["Bông vỗ một cái thật chậm", "Slow clap! — Vỗ chậm"],
        ["Na vỗ ba cái nhanh", "Quick! — Nhanh"],
        ["Bông vỗ ba cái nhanh bằng hai chân", "Quick clap! — Vỗ nhanh"],
        ["Hai bạn nhìn camera, tay sẵn", "Your turn! — Đến lượt bạn"],
        ["Một cái vỗ cuối thật chậm, rồi vẫy", "Slow bye! — Tạm biệt chậm"],
      ]),
    ],
  },
  {
    format: "Trốn và chào",
    from: "Ú òa sau đồ trong vườn, không tối, không sợ",
    clips: [
      clip("Behind the pot", "Sau chậu", "Bông trốn sau chậu rồi chào.", "Thiếu nhi", [
        ["Bông biến mất sau chậu hoa to, chỉ thấy một tai", "Where am I? — Mình ở đâu"],
        ["Na nhìn trái, nhìn phải", "Where is Bông? — Bông đâu"],
        ["Tai Bông nhích lên khỏi chậu", "Peek! — Nhìn trộm"],
        ["Bông nhảy ra và vẫy", "Here I am! — Mình đây"],
        ["Na cười và chỉ camera", "Your turn! — Đến lượt bạn"],
        ["Hai bạn không trốn nữa, đứng giữa sân vẫy", "Hello! — Xin chào"],
      ]),
      clip("Behind the door", "Sau cửa", "Na trốn sau cửa mở.", "Thiếu nhi", [
        ["Chỉ thấy váy hồng sau cánh cửa mở", "Where am I? — Mình ở đâu"],
        ["Bông nhìn vào khe cửa", "Where is Na? — Na đâu"],
        ["Na thò một tay vẫy từ sau cửa", "Peek! — Nhìn trộm"],
        ["Na bước ra cười", "Here I am! — Mình đây"],
        ["Bông vỗ tay", "Found you! — Tìm thấy bạn"],
        ["Hai bạn đóng trò và vẫy ngoài nắng", "Bye! — Tạm biệt"],
      ]),
    ],
  },
  {
    format: "Xếp đồ vào túi",
    from: "Mỗi cảnh một đồ vào túi vải",
    clips: [
      clip("Toy bag", "Túi đồ chơi", "Bóng, hoa giả, sách vào túi.", "Tắt", [
        ["Na mở một túi vải trên thảm", "A bag! — Một cái túi"],
        ["Bông bỏ quả bóng nhỏ vào", "Ball in! — Bóng vào"],
        ["Na bỏ một bông hoa vải vào", "Flower in! — Hoa vào"],
        ["Bông bỏ một cuốn sách mỏng vào", "Book in! — Sách vào"],
        ["Na kéo dây túi", "All in! — Vào hết rồi"],
        ["Hai bạn đeo túi cùng một quai và vẫy", "Let's go! — Mình đi nào"],
      ]),
      clip("Picnic bag", "Túi dã ngoại", "Táo, khăn, bình nước.", "Tắt", [
        ["Bông mở túi trên bậc thềm", "A bag! — Một cái túi"],
        ["Na bỏ quả táo vào", "Apple in! — Táo vào"],
        ["Bông nhét khăn kẻ ô", "Cloth in! — Khăn vào"],
        ["Na đặt bình nước nhỏ vào", "Water in! — Nước vào"],
        ["Túi đầy, hai bạn nhìn vào", "All in! — Vào hết rồi"],
        ["Hai bạn xách túi ra vườn và vẫy", "Picnic time! — Giờ đi chơi"],
      ]),
    ],
  },
  {
    format: "Chia cho bạn",
    from: "Đưa đồ, chờ bạn nhận, rồi cảm ơn",
    clips: [
      clip("Share the apple", "Chia táo", "Một quả, hai bạn.", "Tắt", [
        ["Na cầm quả táo, Bông ngồi đối diện", "I have an apple! — Mình có quả táo"],
        ["Na đưa táo, chưa buông", "Share? — Chia không"],
        ["Bông gật", "Yes, please! — Có, làm ơn"],
        ["Na đặt nửa táo vào chân Bông", "Here! — Đây"],
        ["Bông cúi đầu", "Thank you! — Cảm ơn"],
        ["Hai bạn ăn gió vui và vẫy", "Yummy! — Ngon"],
      ]),
      clip("Share the flower", "Chia hoa", "Na hái một hoa đã rụng, không bẻ cành.", "Tắt", [
        ["Na nhặt một bông hoa đã rụng trên đá", "A flower! — Một bông hoa"],
        ["Na đưa về phía Bông", "For you! — Tặng bạn"],
        ["Bông nhận bằng hai chân", "For me? — Cho mình à"],
        ["Na gật", "Yes! — Đúng"],
        ["Bông giơ hoa lên", "Thank you! — Cảm ơn"],
        ["Bông cài hoa cạnh khăn và hai bạn vẫy", "So kind! — Tử tế quá"],
      ]),
    ],
  },
  {
    format: "Xếp tháp khối",
    from: "Xây, nghiêng, xếp lại, không đổ vào người",
    clips: [
      clip("Stack the blocks", "Xếp khối", "Ba khối gỗ màu trên thảm.", "Thiếu nhi", [
        ["Na đặt khối đỏ xuống thảm", "One! — Một"],
        ["Bông đặt khối vàng lên trên", "Two! — Hai"],
        ["Na đặt khối xanh lên đỉnh", "Three! — Ba"],
        ["Tháp đứng, hai bạn nhìn", "A tower! — Một cái tháp"],
        ["Tháp nghiêng, Na giữ cho không đổ vào ai", "Careful! — Cẩn thận"],
        ["Hai bạn xếp lại thấp hơn và vẫy", "We fixed it! — Mình sửa được"],
      ]),
      clip("A small tower", "Tháp thấp", "Chỉ hai khối, chắc hơn.", "Thiếu nhi", [
        ["Bông đặt khối to làm đế", "Big block! — Khối to"],
        ["Na đặt khối nhỏ lên", "Small block! — Khối nhỏ"],
        ["Hai bạn buông tay, tháp đứng", "It stands! — Nó đứng"],
        ["Na vỗ một cái nhẹ, tháp vẫn đứng", "Strong! — Chắc"],
        ["Bông chỉ tháp", "Say tower! — Hãy nói tower"],
        ["Hai bạn ngồi cạnh tháp và vẫy", "Good job! — Giỏi lắm"],
      ]),
    ],
  },
  {
    format: "Nói vọng lại",
    from: "Na nói, Bông nói nhỏ lại",
    clips: [
      clip("Echo hello", "Vọng hello", "Lời đi từ to đến nhỏ.", "Tắt", [
        ["Na đứng gần camera, miệng mở rõ", "Hello! — Xin chào"],
        ["Bông đứng xa hơn một chút, tai hướng về Na", "Hello! — Xin chào"],
        ["Na nói nhỏ hơn, tay kề miệng", "Hello. — Xin chào"],
        ["Bông thì thầm, vẫn vui", "Hello. — Xin chào"],
        ["Hai bạn cùng nhìn camera", "Say hello! — Hãy nói hello"],
        ["Hai bạn vẫy không nói to nữa", "Bye! — Tạm biệt"],
      ]),
      clip("Echo please", "Vọng please", "Lời làm ơn được nói lại dịu.", "Tắt", [
        ["Na chỉ một bông hoa, nói rõ", "Please! — Làm ơn"],
        ["Bông nhắc lại, chân chỉ cùng hướng", "Please! — Làm ơn"],
        ["Na nói nhẹ hơn khi nhận hoa", "Please. — Làm ơn"],
        ["Bông gật nhẹ", "Please. — Làm ơn"],
        ["Na ôm hoa, nhìn camera", "Say please! — Hãy nói please"],
        ["Hai bạn cúi chào nhỏ", "Thank you! — Cảm ơn"],
      ]),
    ],
  },
  {
    format: "Đúng hay không",
    from: "Yes or no, một câu đúng một câu sai",
    clips: [
      clip("Is Bông a rabbit?", "Bông có phải thỏ", "Câu đúng, rồi một câu sai vui.", "Tắt", [
        ["Na chỉ Bông", "Is this a rabbit? — Đây có phải thỏ không"],
        ["Bông giơ hai tai dài", "Yes! — Đúng"],
        ["Na chỉ một bông hoa", "Is this a shoe? — Đây có phải giày không"],
        ["Bông lắc đầu", "No! — Không"],
        ["Na chỉ giày trắng của mình", "This is a shoe! — Đây mới là giày"],
        ["Hai bạn cười và vẫy", "Yes and no! — Đúng và không"],
      ]),
      clip("Is it raining?", "Có mưa không", "Nắng rõ, câu trả lời là không, rồi đổi.", "Tắt", [
        ["Na nhìn trời xanh", "Is it raining? — Trời có mưa không"],
        ["Bông chỉ nắng trên đá", "No! — Không"],
        ["Na chỉ mặt trời", "It is sunny! — Trời nắng"],
        ["Một đám mây nhỏ kéo tới, vẫn sáng", "A cloud! — Một đám mây"],
        ["Bông chờ, chưa có giọt", "Not yet! — Chưa mà"],
        ["Hai bạn đội mũ và vẫy dưới nắng", "Sunny day! — Ngày nắng"],
      ]),
    ],
  },
  {
    format: "Sáng và tối",
    from: "Cùng ngôi nhà, hai nhịp khác nhau",
    clips: [
      clip("Good morning", "Chào buổi sáng", "Nắng, cửa mở, chơi.", "Thiếu nhi", [
        ["Cửa mở, nắng đầy sân", "Good morning! — Chào buổi sáng"],
        ["Na kéo rèm cửa sổ nhỏ", "Wake up! — Dậy nào"],
        ["Bông bước ra, khăn đã quàng", "I am up! — Mình dậy rồi"],
        ["Hai bạn tưới hoa một vòng", "Good morning, flowers! — Chào các hoa"],
        ["Na vẫy người xem", "Say good morning! — Hãy nói good morning"],
        ["Hai bạn chạy chậm ra cổng", "Let's play! — Mình chơi nào"],
      ]),
      clip("Good night", "Chào buổi tối", "Trời tím nhẹ, không ma, không tối đen.", "Tắt", [
        ["Trời tím sau hàng rào, cửa còn hé", "Good night! — Chúc ngủ ngon"],
        ["Na xếp giày trắng ngay ngắn", "Shoes away! — Cất giày"],
        ["Bông gấp khăn xanh lên ghế", "Scarf away! — Cất khăn"],
        ["Na kéo chăn nhỏ trên ghế gỗ", "Cozy! — Ấm rồi"],
        ["Hai bạn thì thầm nhìn camera", "Say good night! — Hãy nói good night"],
        ["Cửa khép, một khe đèn ấm còn lại, hai bạn vẫy trong khe", "Sweet dreams! — Ngủ ngon"],
      ]),
    ],
  },
  {
    format: "Chuỗi lời tử tế",
    from: "Một chuyện dùng nhiều lời, không luyện một từ",
    clips: [
      clip("A kind visit", "Đến chơi tử tế", "Chào, xin, cảm ơn, xin lỗi, ồ, tạm biệt.", "Thiếu nhi", [
        ["Na mở cổng, Bông đứng trong sân", "Hello! — Xin chào"],
        ["Na chỉ hoa, chưa lấy", "Please! — Làm ơn"],
        ["Bông đưa một hoa đã rụng", "Thank you! — Cảm ơn"],
        ["Na vô tình dẫm cánh hoa và dừng lại", "Sorry! — Xin lỗi"],
        ["Bông gật, Na thở phào", "Wow, thank you! — Ồ, cảm ơn"],
        ["Na ra cổng và vẫy", "Goodbye! — Tạm biệt"],
      ]),
      clip("A kind game", "Chơi tử tế", "Xin lượt, chia bóng, xin lỗi, khen.", "Thiếu nhi", [
        ["Bông đứng cạnh bóng, Na chờ", "My turn? — Đến lượt mình không"],
        ["Na gật và lùi", "Yes, please! — Có, mời bạn"],
        ["Bông lăn bóng cho Na", "Your turn! — Đến lượt bạn"],
        ["Bóng chạm chậu, Na giữ lại", "Sorry! — Xin lỗi"],
        ["Bông vỗ tay vì Na giữ được bóng", "Good job! — Giỏi lắm"],
        ["Hai bạn bỏ bóng vào giỏ và vẫy", "Bye! — Tạm biệt"],
      ]),
    ],
  },
  {
    format: "Lễ hoàn thành",
    from: "Kết một tháng, một video rộn và một video dịu",
    clips: [
      clip("We did it", "Mình làm được", "Vỗ, nhảy, xoay, cúi, vẫy.", "Thiếu nhi", [
        ["Na và Bông đứng giữa vườn đầy hoa", "We did it! — Mình làm được"],
        ["Hai bạn vỗ tay và vỗ chân", "Clap! — Vỗ tay"],
        ["Hai bạn nhảy một nhịp cùng lúc", "Jump! — Nhảy"],
        ["Hai bạn xoay một vòng chậm", "Spin! — Xoay"],
        ["Hai bạn cúi chào người xem", "Thank you! — Cảm ơn"],
        ["Hai bạn vẫy thật rộng, Bông lùi về cửa", "Goodbye! — Tạm biệt"],
      ]),
      clip("Quiet good job", "Khen khẽ", "Ngồi trên bậc, nói nhỏ, vẫn vui.", "Tắt", [
        ["Na và Bông ngồi trên bậc thềm, hoa quanh", "Good job! — Giỏi lắm"],
        ["Na đặt một hoa đã rụng lên chân Bông", "For you! — Tặng bạn"],
        ["Bông đặt một lá lên giày Na", "For you! — Tặng bạn"],
        ["Hai bạn nhìn nhau cười không nhảy", "Friends! — Bạn bè"],
        ["Na thì thầm về phía camera", "You did it! — Bạn làm được"],
        ["Cửa hé đèn ấm, hai bạn vẫy nhỏ", "Good night! — Ngủ ngon"],
      ]),
    ],
  },
];

function scriptOf(item: Clip): string {
  return item.scenes.map(([draw, line]) => `Vẽ: ${draw}\nĐọc: ${line}`).join("\n\n");
}

export default function KeHoach30Ngay() {
  const [day, setDay] = useCanvasState("day", "1");
  const [slot, setSlot] = useCanvasState("slot", "0");
  const index = Math.max(0, Math.min(DAYS.length - 1, Number(day) - 1 || 0));
  const plan = DAYS[index];
  const current = plan.clips[slot === "1" ? 1 : 0];

  return (
    <Stack gap={20}>
      <Stack gap={6}>
        <H1>30 ngày tiếng Anh, mỗi ngày một dạng</H1>
        <Text>
          Hai video mỗi ngày, sáu cảnh mỗi video, đúng 12 cảnh chuyển động. Lời viết mới cho Na và Bông. Dạng lấy từ Shorts và TikTok, không chép kịch bản của kênh khác.
        </Text>
      </Stack>
      <Row gap={16}>
        <Stat value="30" label="Ngày, mỗi ngày một dạng" />
        <Stat value="60" label="Video trong tháng" />
        <Stat value="12" label="Cảnh Wan mỗi ngày" />
        <Stat value="360" label="Cảnh cả 30 ngày" />
      </Row>
      <Callout tone="info">
        Trong tool: Số cảnh 6, Giây mỗi cảnh 5, phụ đề tiếng Anh từng từ bật. Nhạc theo dòng của video đang chọn. Dán hồ sơ nhân vật một lần, rồi dán kịch bản bên dưới.
      </Callout>
      <TextArea value={LOCK} rows={3} />
      <H2>Video cần dựng</H2>
      <Row gap={8} align="center">
        <Select
          value={String(index + 1)}
          onChange={setDay}
          options={DAYS.map((item, itemIndex) => ({
            value: String(itemIndex + 1),
            label: `Ngày ${itemIndex + 1} — ${item.format}`,
          }))}
        />
        <Button variant={slot === "1" ? "secondary" : "primary"} onClick={() => setSlot("0")}>
          Video 1
        </Button>
        <Button variant={slot === "1" ? "primary" : "secondary"} onClick={() => setSlot("1")}>
          Video 2
        </Button>
      </Row>
      <Stack gap={4}>
        <H3>{`Ngày ${index + 1} · ${current.title}`}</H3>
        <Text>{`Dạng: ${plan.format}. Gợi ý từ ${plan.from}.`}</Text>
        <Text>{`Chủ đề: ${current.theme}. ${current.overview}`}</Text>
        <Text weight="semibold">{`Nhạc nền: ${current.music}`}</Text>
      </Stack>
      <TextArea value={scriptOf(current)} rows={18} />
      <H2>Lịch cả tháng</H2>
      <Table
        headers={["Ngày", "Dạng", "Video 1", "Video 2", "Nguồn dạng"]}
        columnAlign={["right", "left", "left", "left", "left"]}
        striped
        stickyHeader
        rows={DAYS.map((item, itemIndex) => [
          String(itemIndex + 1),
          item.format,
          item.clips[0].title,
          item.clips[1].title,
          item.from,
        ])}
      />
      <Text tone="tertiary">
        Dạng công khai đã xem: câu đố What am I, từ trái nghĩa diễn bằng người, làm theo tôi, tìm đồ, chờ đến cuối. Mỗi ngày đổi nhịp kể. Hết 12 cảnh thì dừng, hôm sau làm ngày kế tiếp.
      </Text>
    </Stack>
  );
}
