import {
  Activity,
  BarChart3,
  Camera,
  ChevronRight,
  CircleDot,
  ClipboardCheck,
  Cpu,
  Gauge,
  LineChart,
  MonitorPlay,
  MoveHorizontal,
  RadioTower,
  ScanLine,
  Timer,
  Waves
} from "lucide-react";

export const navLinks = [
  { label: "SYSTEM", href: "#system" },
  { label: "FEATURES", href: "#features" },
  { label: "OUTPUT", href: "#analysis" },
  { label: "FAQ", href: "#faq" }
];

export const workflowSteps = [
  {
    eyebrow: "01 / LANE-SIDE CART",
    title: "岸边移动跟随",
    description: "操作员沿泳道推动带滑轮采集车，保持侧面连续视角跟随运动员游进。",
    Icon: MoveHorizontal
  },
  {
    eyebrow: "02 / DUAL CAMERA",
    title: "水上水下双摄",
    description: "上方摄像头记录身体出水动作，下方摄像头补足划水、打腿与身体线条。",
    Icon: Camera
  },
  {
    eyebrow: "03 / STITCHED VIEW",
    title: "自动拼接侧面视频",
    description: "双路画面同步后形成完整侧面训练视频，减少单一固定机位的信息缺失。",
    Icon: MonitorPlay
  },
  {
    eyebrow: "04 / AI ANALYSIS",
    title: "姿态识别与评估",
    description: "视频传输到运算设备，提取关键点、角度与节奏指标，辅助教练复盘。",
    Icon: Cpu
  }
];

export const features = [
  {
    title: "DUAL-VIEW CAPTURE",
    description: "水上与水下摄像头同步采集，从完整侧面视角记录运动员动作。",
    Icon: Waves
  },
  {
    title: "LANE-SIDE MOTION TRACKING",
    description: "移动采集车沿泳道跟随拍摄，覆盖连续游进过程，而不是固定点片段。",
    Icon: RadioTower
  },
  {
    title: "AI POSE ANALYSIS",
    description: "基于姿态识别算法提取人体关键点，辅助教练分析动作结构与技术细节。",
    Icon: Activity
  }
];

export const specs = [
  ["CAMERA CONFIGURATION", "水上 + 水下双摄"],
  ["CAPTURE VIEW", "侧面连续视角"],
  ["VIDEO OUTPUT", "自动拼接泳姿视频"],
  ["ANALYSIS ENGINE", "姿态关键点识别"],
  ["DEPLOYMENT", "泳池岸边移动采集"],
  ["COMPUTING DEVICE", "外接运算设备 / 工作站"],
  ["TARGET USERS", "教练 / 运动队 / 科研团队"]
];

export const analysisOutputs = [
  {
    label: "KEYPOINT TRAJECTORY",
    title: "关键点轨迹",
    description: "追踪肩、肘、腕、髋、膝、踝等关键点随游进过程的变化。",
    Icon: ScanLine
  },
  {
    label: "BODY ANGLES",
    title: "身体角度",
    description: "辅助观察入水、划水、换气、打腿等阶段的身体姿态。",
    Icon: Gauge
  },
  {
    label: "STROKE RHYTHM",
    title: "划水节奏",
    description: "从连续侧面视频中提取节奏线索，服务训练周期对比。",
    Icon: Timer
  },
  {
    label: "SYMMETRY CUES",
    title: "动作对称性",
    description: "为教练提供左右动作差异与技术稳定性的观察依据。",
    Icon: LineChart
  },
  {
    label: "SIDE-VIEW REPLAY",
    title: "侧面回放",
    description: "拼接后的训练视频可用于逐帧复盘和动作讲解。",
    Icon: MonitorPlay
  },
  {
    label: "COACH REVIEW",
    title: "训练复盘",
    description: "将视频、关键点和指标组织成更容易讨论的训练材料。",
    Icon: ClipboardCheck
  }
];

export const testimonials = [
  {
    quote: "完整侧面视角让技术复盘更直接，尤其是水下划水和身体线条的连续变化。",
    name: "LIANG COACH",
    role: "高校游泳队教练"
  },
  {
    quote: "固定机位很难看清整段游进过程，移动双摄方案更接近真实训练场景。",
    name: "SPORT SCIENCE LAB",
    role: "运动科学实验室"
  },
  {
    quote: "视频和姿态数据结合后，队员能更快理解自己动作的问题在哪里。",
    name: "YOUTH TEAM",
    role: "青训俱乐部"
  }
];

export const videoHighlights = [
  { text: "双路采集同步", Icon: CircleDot },
  { text: "侧面视频拼接", Icon: ChevronRight },
  { text: "AI姿态识别", Icon: BarChart3 }
];

export const faqItems = [
  {
    question: "智泳云枢如何部署在泳池边？",
    answer:
      "系统通过带滑轮的小推车沿泳道岸边移动，上下两个摄像头分别覆盖水上和水下画面，操作员跟随运动员推进即可完成连续采集。"
  },
  {
    question: "水下摄像头是否适合长期训练采集？",
    answer:
      "官网首版会以系统能力介绍为主，具体防水等级和硬件参数可在真实设备定型后替换到规格区块。"
  },
  {
    question: "采集后的视频在哪里分析？",
    answer:
      "双摄画面传输到外接运算设备或工作站，完成视频拼接、姿态关键点识别和训练复盘材料生成。"
  },
  {
    question: "系统是否需要运动员佩戴设备？",
    answer:
      "当前定位是视觉采集和姿态分析方案，页面不承诺穿戴设备能力，重点展示非接触式视频分析流程。"
  },
  {
    question: "可以替换成真实产品视频吗？",
    answer:
      "可以。页面会使用稳定比例的媒体容器，后续可直接替换为真实小车、泳池拍摄或算法演示视频。"
  }
];

export const footerGroups = [
  {
    title: "PRODUCT",
    links: ["System Flow", "Dual Camera", "AI Analysis", "Field Test"]
  },
  {
    title: "SUPPORT",
    links: ["Deployment", "Hardware Specs", "Training Setup", "Contact"]
  }
];
