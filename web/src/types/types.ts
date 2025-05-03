// types.ts
// types.ts
export interface Message {
  type: "text" | "image" | "file" | "thinking" | "baseFile";
  content: string | null;
  thinking?: string;
  fileName?: string; // 新增文件名字段
  fileType?: string; // 新增文件类型字段
  minioUrl?: string;
  messageId?: string;
  baseId?: string;
  score?: number;
  imageMinioUrl?: string;
  token_number?: {
    total_token: number;
    completion_tokens: number;
    prompt_tokens: number;
  };
  from: "user" | "ai"; // 消息的来源
}

export interface Chat {
  name: string;
  conversationId: string;
  lastModityTime: string;
  isRead: boolean;
  createTime: string;
  messages: Message[];
}

export interface Base {
  name: string;
  baseId: string;
  lastModityTime: string;
  createTime: string;
  fileNumber: number;
}

export interface KnowledgeBase {
  id: string;
  name: string;
  selected: boolean;
}

export interface BaseUsed {
  name: string;
  baseId: string;
}

export interface FileRespose {
  id: string;
  minio_filename: string;
  filename: string;
  url: string;
}

// 更新类型定义
export interface ModelConfig {
  modelId: string;
  baseUsed: BaseUsed[];
  modelName: string;
  modelURL: string;
  apiKey: string;
  systemPrompt: string;
  temperature: number;
  maxLength: number;
  topP: number;
  topK: number;
  useTemperatureDefault: boolean;
  useMaxLengthDefault: boolean;
  useTopPDefault: boolean;
  useTopKDefault: boolean;
}

export interface UploadFile {
  id: string;
  name: string;
  progress: number;
  error?: string;
}

export interface KnowledgeFile {
  file_id: string;
  filename: string;
  url: string;
  upload_time: string;
  kb_id: string;
  minio_filename: string;
}

export interface FileUsed {
  knowledge_db_id: string;
  file_name: string;
  image_url: string;
  file_url: string;
  score: number;
}

// types.ts
import { Node, Edge, NodeProps, EdgeProps } from "@xyflow/react";

export type NodeTypeKey =
  | "start"
  | "end"
  | "loop"
  | "condition"
  | "vlm"
  | "code";

// 完整节点类型（继承基础节点属性）
export type CustomNode = Node<{
  label: string;
  nodeType: NodeTypeKey;
  code?: string;
  output?: string;
  conditionCount?: number;
  conditions?:  {
    [key: number]: string; // 允许动态属性
  };
  loopType?: string;
  maxCount?: number;
  condition?: string;

}>;

// 组件 Props 类型
export type CustomNodeProps = NodeProps<CustomNode>;

// 边类型
export type CustomEdge = Edge<{
  conditionLabel?: string;
  loopType?: string;
}>;

export type CustomEdgeProps = EdgeProps<CustomEdge>;

export interface sendNode {
  id: string;
  type: string;
  data: {
    code?: string;
  };
}

export interface sendEdges {
  source: string;
  target: string;
  sourceHandle?: string;
}

// 节点类型配置
export const nodeTypesInfo: Record<
  NodeTypeKey,
  {
    label: string;
  }
> = {
  start: { label: "Start" },
  end: { label: "End" },
  loop: { label: "Loop" },
  condition: { label: "Condition" },
  vlm: { label: "VLM" },
  code: { label: "Code" },
};

export interface Flow {
  name: string;
  flowId: string;
  lastModityTime: string;
  createTime: string;
  fileNumber: number;
}
