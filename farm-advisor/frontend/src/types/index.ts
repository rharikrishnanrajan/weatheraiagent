export interface FarmProfile {
  id: number;
  farmer_name: string;
  location_name: string;
  latitude: number;
  longitude: number;
  crops: string[];
  field_size_hectares: number;
  soil_type: string;
  irrigation_type: string;
  preferred_language: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface WeatherCurrent {
  time: string;
  temperature_2m: number;
  relative_humidity_2m: number;
  apparent_temperature: number;
  precipitation: number;
  rain: number;
  weather_code: number;
  weather_description: string;
  cloud_cover: number;
  wind_speed_10m: number;
  wind_gusts_10m: number;
  wind_direction_10m: number;
}

export interface WeatherDailyItem {
  date: string;
  weather_code: number;
  weather_description: string;
  temperature_2m_max: number;
  temperature_2m_min: number;
  apparent_temperature_max: number;
  apparent_temperature_min: number;
  precipitation_sum: number;
  precipitation_probability_max?: number;
  wind_speed_10m_max: number;
  et0_fao_evapotranspiration?: number;
  uv_index_max?: number;
}

export interface WeatherHourlyItem {
  time: string;
  temperature_2m: number;
  relative_humidity_2m: number;
  precipitation_probability: number;
  precipitation: number;
  wind_speed_10m: number;
  wind_gusts_10m: number;
  soil_temperature_0cm?: number;
  soil_moisture_0_to_1cm?: number;
}

export interface WeatherAlert {
  category: string;
  severity: 'Low' | 'Moderate' | 'High' | 'Severe' | string;
  title: string;
  description: string;
  action_recommendation: string;
  valid_time?: string;
}

export interface WeatherData {
  location: {
    name: string;
    latitude: number;
    longitude: number;
    country?: string;
    admin1?: string;
    elevation?: number;
  };
  current: WeatherCurrent;
  daily: WeatherDailyItem[];
  hourly_recent_or_upcoming: WeatherHourlyItem[];
  alerts: WeatherAlert[];
}

export interface ToolExecution {
  tool: string;
  label?: string;
  status: 'running' | 'completed' | 'error';
  input?: Record<string, unknown>;
  output_preview?: string;
}

export interface ChatMessage {
  id?: string | number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: string[];
  tool_calls?: ToolExecution[];
  created_at?: string;
}

export interface ThreadItem {
  thread_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface KnowledgeDoc {
  id: string;
  filename: string;
  title: string;
  category: string;
  crops: string[];
  size_bytes: number;
  chunk_count: number;
  created_at: string;
}

export interface KnowledgeSearchResult {
  source: string;
  title: string;
  category: string;
  crop: string;
  content: string;
  score: number;
}
