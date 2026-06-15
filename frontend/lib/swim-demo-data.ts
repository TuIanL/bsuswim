import type {
  SwimAnalysisReport,
  SwimAnalysisStage,
  SwimCaptureMode,
  SwimMetric,
  SwimStrokeType
} from "@/lib/swim-types";

export const strokeLabels: Record<SwimStrokeType, string> = {
  freestyle: "自由泳",
  backstroke: "仰泳",
  breaststroke: "蛙泳",
  butterfly: "蝶泳",
  mixed: "混合泳"
};

export const captureModeLabels: Record<SwimCaptureMode, string> = {
  "dual-camera-cart": "岸边移动双摄",
  "above-water": "水上侧面视角",
  underwater: "水下侧面视角",
  "stitched-side-view": "拼接侧面视频"
};

export const swimStageBlueprint: SwimAnalysisStage[] = [
  {
    id: "upload",
    label: "视频上传",
    status: "done",
    detail: "保存训练视频与基础会话信息",
    progress: 100
  },
  {
    id: "sync",
    label: "双路同步",
    status: "done",
    detail: "对齐水上与水下画面时间轴",
    progress: 100
  },
  {
    id: "stitching",
    label: "侧面拼接",
    status: "done",
    detail: "生成可复盘的连续侧面泳姿视图",
    progress: 100
  },
  {
    id: "frame-sampling",
    label: "抽帧采样",
    status: "done",
    detail: "按训练节奏提取关键帧",
    progress: 100
  },
  {
    id: "pose",
    label: "姿态检测",
    status: "done",
    detail: "识别肩、肘、腕、髋、膝、踝等关键点",
    progress: 100
  },
  {
    id: "stroke-segmentation",
    label: "划水分段",
    status: "done",
    detail: "定位入水、抱水、推水、换气和打腿节奏",
    progress: 100
  },
  {
    id: "metrics",
    label: "指标提取",
    status: "done",
    detail: "计算身体角度、节奏稳定性和左右对称性",
    progress: 100
  },
  {
    id: "visualization",
    label: "可视化输出",
    status: "done",
    detail: "组织关键点、节奏线和教练提示",
    progress: 100
  },
  {
    id: "report",
    label: "报告生成",
    status: "done",
    detail: "生成训练复盘与下一次练习建议",
    progress: 100
  }
];

export const demoSwimReport: SwimAnalysisReport = {
  id: "ZY-DEMO-20260615",
  source: "demo",
  session: {
    fileName: "demo-side-view-freestyle.mp4",
    fileSize: 148_600_000,
    sessionTitle: "自由泳连续侧面技术样本",
    venue: "北京体育大学游泳馆",
    sessionDate: "2026-06-15",
    swimmerLabel: "青训运动员 A",
    strokeType: "freestyle",
    level: "专项提高",
    captureMode: "dual-camera-cart"
  },
  summary:
    "本次样例聚焦连续侧面视角下的身体线条、换气节奏、入水角度和打腿稳定性，用于展示智泳云枢平台工作流。",
  metrics: [
    {
      id: "overall",
      label: "技术评分",
      value: "86",
      detail: "身体线条与划水节奏整体稳定",
      trend: "+6",
      tone: "strong"
    },
    {
      id: "rhythm",
      label: "划水节奏",
      value: "1.18s",
      detail: "平均单次划水周期",
      trend: "-0.08s",
      tone: "strong"
    },
    {
      id: "body-angle",
      label: "身体角度稳定",
      value: "78%",
      detail: "换气阶段存在轻微抬头",
      trend: "+4%",
      tone: "watch"
    },
    {
      id: "symmetry",
      label: "左右对称",
      value: "82%",
      detail: "右侧入水路径略向外偏",
      trend: "+3%",
      tone: "neutral"
    },
    {
      id: "kick",
      label: "打腿连续性",
      value: "74%",
      detail: "后半程节奏有两次下降",
      trend: "-5%",
      tone: "risk"
    }
  ] satisfies SwimMetric[],
  diagnostics: [
    {
      id: "breathing-head-lift",
      title: "换气时头部抬升",
      severity: "中",
      evidence: "第 18-24 秒换气阶段头肩连线抬升，身体流线短暂破坏。",
      suggestion: "以单侧换气节奏练习保持头部贴近水面旋转，减少向上抬头。",
      expectedOutcome: "降低换气阻力，提升连续游进速度稳定性。",
      priority: "优先级 1"
    },
    {
      id: "right-hand-entry",
      title: "右手入水外摆",
      severity: "中",
      evidence: "右手入水点相对肩线偏外，后续抱水路径变长。",
      suggestion: "加入前伸定位和肩宽入水练习，保持手臂进入身体中轴外侧合理区域。",
      expectedOutcome: "提升抱水效率，减少横向摆动。",
      priority: "优先级 2"
    },
    {
      id: "late-kick-drop",
      title: "后程打腿节奏下降",
      severity: "低",
      evidence: "第 34 秒后踝部关键点振幅减小，节奏线出现间隔拉长。",
      suggestion: "用 6 次腿配合单臂划水训练稳定后程腿部节拍。",
      expectedOutcome: "改善后程推进连续性。",
      priority: "优先级 3"
    }
  ],
  recommendations: [
    {
      id: "tr-breathing",
      issueId: "breathing-head-lift",
      title: "低头侧转换气练习",
      learningContent: "视频对标：头部贴水旋转与肩髋协同",
      practiceTask: "4 组 25 米单侧换气，要求换气时一侧镜片留在水中。",
      nextTarget: "换气阶段身体角度稳定性提升到 84%",
      progress: {
        previous: 71,
        current: 78,
        target: 84,
        unit: "%"
      }
    },
    {
      id: "tr-entry",
      issueId: "right-hand-entry",
      title: "肩宽入水定位",
      learningContent: "动作对标：手掌入水点与肩线关系",
      practiceTask: "3 组 8 次前伸停顿划水，观察右手入水是否越过肩线。",
      nextTarget: "右侧入水路径偏移降低 20%",
      progress: {
        previous: 62,
        current: 70,
        target: 82,
        unit: "%"
      }
    }
  ],
  visualLayers: [
    {
      id: "source",
      label: "拼接侧面视频",
      state: "demo",
      detail: "演示数据：水上/水下画面同步后的连续侧面视角"
    },
    {
      id: "keypoints",
      label: "关键点轨迹",
      state: "demo",
      detail: "肩、肘、腕、髋、膝、踝关键点示意"
    },
    {
      id: "rhythm",
      label: "划水节奏线",
      state: "demo",
      detail: "入水、抱水、推水、换气阶段节奏标记"
    },
    {
      id: "symmetry",
      label: "对称性提示",
      state: "limited",
      detail: "样例仅展示左右动作差异提示，等待真实算法接入"
    }
  ],
  overlayCues: [
    {
      id: "cue-body-line",
      label: "身体线条稳定",
      detail: "髋部未明显下沉",
      x: 50,
      y: 42,
      tone: "strong"
    },
    {
      id: "cue-breath",
      label: "换气抬头",
      detail: "建议降低头部上抬",
      x: 67,
      y: 27,
      tone: "watch"
    },
    {
      id: "cue-kick",
      label: "后程打腿减弱",
      detail: "节奏线间隔变长",
      x: 29,
      y: 68,
      tone: "risk"
    }
  ],
  rhythmTicks: [
    { id: "tick-1", label: "入水", position: 12, tone: "strong" },
    { id: "tick-2", label: "抱水", position: 28, tone: "neutral" },
    { id: "tick-3", label: "推水", position: 46, tone: "strong" },
    { id: "tick-4", label: "换气", position: 63, tone: "watch" },
    { id: "tick-5", label: "打腿", position: 82, tone: "risk" }
  ],
  keyFindings: [
    "连续侧面视角能稳定呈现水上身体线条与水下划水轨迹。",
    "换气阶段是当前最值得优先处理的技术点。",
    "后程打腿节奏下降会影响推进连续性，建议进入下一次训练目标。"
  ]
};

export function cloneReportForSession(reportId: string, session: SwimAnalysisReport["session"]): SwimAnalysisReport {
  return {
    ...demoSwimReport,
    id: reportId,
    source: "local-job",
    session,
    summary: `${session.sessionTitle} 已生成本地演示分析。当前结果使用智泳云枢样例模型输出结构，后续可替换为真实算法服务。`
  };
}
