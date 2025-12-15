# YOLOv11 Object Detection and Speed Estimation

YOLOv11-Speed is a comprehensive real-time object detection, tracking, and speed estimation system optimized for Hailo AI accelerators. This project enables efficient detection of objects (with focus on persons and vehicles) with simultaneous tracking and speed calculation capabilities.

## ✨ Features

- **Real-time Object Detection**: Using optimized YOLOv11 models for fast inference
- **Multi-Object Tracking**: BYTE (ByteTrack) tracking algorithm for consistent object identification across frames
- **Speed Estimation**: Advanced speed calculation for tracked objects using pixel-to-real-world distance conversion
- **Flexible Input Support**: Images, videos, and camera streams
- **Configurable Labels**: Support for detecting specific object classes (default: person, car)
- **Performance Optimized**: Designed for Hailo AI accelerators for high-performance inference

## 📁 Project Structure

```
YOLOv11-Speed/
├── LICENSE                    # MIT License
├── README.md                 # Project documentation
├── docker-compose.yml        # Docker orchestration
├── Docker.md                 # Docker documentation
├── Dockerfile               # Docker build configuration
├── requirements.txt         # Python dependencies
├── run_detection.py         # Main entry point (CLI)
├── run_api.py              # API server entry point
├── .env/                    # Environment configuration
├── .github/                 # GitHub workflows and actions
├── output/                  # Output directory for results
└── src/                     # Source code directory
    ├── __init__.py
    ├── object_detection.py              # Main detection pipeline
    ├── object_detection_post_process.py # Post-processing and visualization
    ├── speed_estimation.py             # Speed calculation algorithms
    ├── api_server.py                   # Flask API server for web integration
    ├── config/                        # Configuration files
    │   ├── __init__.py
    │   ├── config.json                # Detection and tracking parameters
    │   └── coco.txt                   # COCO dataset labels
    ├── models/                        # Model files
    │   ├── __init__.py
    │   └── yolov11n.hef              # Optimized YOLOv11 model for Hailo
    ├── tracker/                       # Object tracking modules
    │   ├── __init__.py
    │   ├── byte_tracker.py           # BYTE tracker implementation
    │   ├── kalman_filter.py          # Kalman filter for motion prediction
    │   ├── matching.py               # Track matching algorithms
    │   └── basetrack.py              # Base tracking class
    ├── utils/                         # Utility functions
    │   ├── __init__.py
    │   ├── hailo_inference.py        # Hailo inference wrapper
    │   └── toolbox.py                # Common utilities and helper functions
    └── __pycache__/                 # Python cache files
```

## 🛠️ Requirements

### Hardware
- Hailo AI accelerator (Hailo-8 or Hailo-10)
- Compatible PCIe slot for Hailo card
- Camera or video input (for streaming applications)

### Software
- **Python**: 3.8 or higher
- **HailoRT**: Version 4.22.0 or compatible
- **Dependencies**: Listed in `requirements.txt`

### System Dependencies
- Linux operating system (tested on Ubuntu)
- OpenCV-compatible camera drivers (for camera input)
- Graphics acceleration (for visualization)

## 📦 Installation

### Prerequisites
1. Install Hailo PCIe driver and PyHailoRT from the [Hailo website](https://hailo.ai/developer-zone/)
2. Ensure your system has a compatible Hailo accelerator installed

### Setup Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/YOLOv11-Speed.git
   cd YOLOv11-Speed
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Ensure the required model file is available in `src/models/` (the repository includes `yolov11n.hef`)

## 🚀 Usage

### Basic Object Detection
```bash
# Run detection on an image
python run_detection.py -i src/data/bus.jpg -n src/models/yolov11n.hef

# Run detection on a video
python run_detection.py -i src/data/full_mov_slow.mp4 -n src/models/yolov11n.hef
```

### Enable Tracking
```bash
# Detection with object tracking
python run_detection.py -i src/data/bus.jpg -n src/models/yolov11n.hef --track

# Tracking with video input
python run_detection.py -i src/data/full_mov_slow.mp4 -n src/models/yolov11n.hef --track
```

### Speed Estimation
```bash
# Detection with tracking and speed estimation (default: person, car)
python run_detection.py -i camera -n src/models/yolov11n.hef --track --speed-estimation

# With custom pixel distance calibration (e.g., 0.02 meters per pixel)
python run_detection.py -i src/data/video.mp4 -n src/models/yolov11n.hef --track --speed-estimation --pixel-distance 0.02
```

### Custom Labels
```bash
# Detect specific classes (e.g., bird, car, person)
python run_detection.py -i camera -n src/models/yolov11n.hef --track --speed-estimation --label bird car person

# Detect only cars
python run_detection.py -i camera -n src/models/yolov11n.hef --track --speed-estimation --label car
```

### Camera Input
```bash
# From USB camera with custom resolution
python run_detection.py -i camera -n src/models/yolov11n.hef --track --resolution hd --camera-width 1280 --camera-height 720

# With FPS display
python run_detection.py -i camera -n src/models/yolov11n.hef --track --show-fps
```

## 🌐 Web API Usage

The project includes a Flask-based REST API server for frontend integration. The API provides endpoints for controlling detection, configuring parameters, and streaming video.

### Starting the API Server

```bash
# Start the API server
python run_api.py
```

The server will start on `http://0.0.0.0:5000` by default.

### Web Interface

The API server includes a modern, responsive web interface for easy interaction with the detection system. Access it at `http://localhost:5000/` after starting the server.

**Features of the Web Interface:**
- Real-time video streaming from the detection system
- Start/stop detection controls
- Configuration of detection parameters (confidence threshold, pixel distance, etc.)
- Toggle for tracking and speed estimation features
- Ability to specify target labels (person, car, etc.)
- Real-time statistics display (FPS, number of viewers)
- Status indicators for system state
- Mobile-responsive design

### API Endpoints

#### 1. Get Status
```http
GET /api/status
```
Returns the current detection status, configuration, and FPS.

**Response:**
```json
{
  "running": false,
  "config": {
    "video_source": "camera",
    "confidence_threshold": 0.25,
    "pixel_distance_mm": 10.0,
    "enable_tracking": true,
    "enable_speed_estimation": true,
    "target_labels": ["person", "car"]
  },
  "fps": 0.0
}
```

#### 2. Start Detection
```http
POST /api/start
```
Starts the detection pipeline with current configuration.

**Response:**
```json
{
  "message": "Detection started successfully",
  "status": "running"
}
```

#### 3. Stop Detection
```http
POST /api/stop
```
Stops the detection pipeline.

**Response:**
```json
{
  "message": "Detection stopped successfully",
  "status": "stopped"
}
```

#### 4. Get Configuration
```http
GET /api/config
```
Returns the current configuration.

#### 5. Update Configuration
```http
POST /api/config
Content-Type: application/json

{
  "video_source": "camera",           // "camera" or video file path
  "confidence_threshold": 0.3,         // 0.0 to 1.0 (can be updated while running)
  "pixel_distance_mm": 15.0,          // millimeters per pixel (can be updated in real-time)
  "enable_tracking": true,             // requires restart
  "enable_speed_estimation": true,     // requires restart
  "target_labels": ["person", "car"]  // requires restart
}
```

**Note:** Some configuration changes require stopping and restarting detection:
- `video_source`: Must stop detection first
- `enable_tracking`: Must stop detection first
- `enable_speed_estimation`: Must stop detection first
- `target_labels`: Must stop detection first
- `confidence_threshold`: Can be updated in real-time
- `pixel_distance_mm`: Can be updated in real-time

#### 6. Video Stream
```http
GET /api/video_stream
```
Returns an MJPEG video stream of the detection results. Use this in an HTML `<img>` tag:

```html
<img src="http://localhost:5000/api/video_stream" alt="Video Stream" />
```

#### 7. Health Check
```http
GET /api/health
```
Returns server health status.

### Frontend Integration Example

```javascript
// Start detection
async function startDetection() {
  const response = await fetch('http://localhost:5000/api/start', {
    method: 'POST'
  });
  const data = await response.json();
  console.log(data);
}

// Stop detection
async function stopDetection() {
  const response = await fetch('http://localhost:5000/api/stop', {
    method: 'POST'
  });
  const data = await response.json();
  console.log(data);
}

// Update confidence threshold (real-time)
async function updateConfidence(threshold) {
  const response = await fetch('http://localhost:5000/api/config', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      confidence_threshold: threshold
    })
  });
  const data = await response.json();
  console.log(data);
}

// Update pixel distance (real-time)
async function updatePixelDistance(mm) {
  const response = await fetch('http://localhost:5000/api/config', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      pixel_distance_mm: mm
    })
  });
  const data = await response.json();
  console.log(data);
}

// Configure video source (requires restart)
async function setVideoSource(source) {
  // First stop detection
  await stopDetection();

  // Update config
  const response = await fetch('http://localhost:5000/api/config', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      video_source: source  // "camera" or "/path/to/video.mp4"
    })
  });
  const data = await response.json();
  console.log(data);

  // Restart detection
  await startDetection();
}

// Get status
async function getStatus() {
  const response = await fetch('http://localhost:5000/api/status');
  const data = await response.json();
  return data;
}
```

### HTML Example

```html
<!DOCTYPE html>
<html>
<head>
  <title>YOLOv11 Detection</title>
</head>
<body>
  <div>
    <button onclick="startDetection()">Start Detection</button>
    <button onclick="stopDetection()">Stop Detection</button>
  </div>
  
  <div>
    <label>Confidence Threshold:</label>
    <input type="range" min="0" max="1" step="0.01" value="0.25" 
           onchange="updateConfidence(this.value)">
    <span id="confidenceValue">0.25</span>
  </div>
  
  <div>
    <label>Pixel Distance (mm):</label>
    <input type="number" value="10" min="1" max="100" 
           onchange="updatePixelDistance(this.value)">
  </div>
  
  <div>
    <img id="videoStream" src="http://localhost:5000/api/video_stream" 
         alt="Video Stream" style="max-width: 100%;">
  </div>
  
  <script>
    // Include the JavaScript functions from above
    // ...
  </script>
</body>
</html>
```

## ⚙️ Configuration

The `src/config/config.json` file contains parameters for:

- **Detection settings**:
  - `score_thres`: Minimum confidence threshold for detections (default: 0.25)
  - `max_boxes_to_draw`: Maximum number of detection boxes to render (default: 500)

- **Tracking settings**:
  - `track_thresh`: Detection confidence threshold for tracking (default: 0.1)
  - `track_buffer`: Number of frames to buffer for tracking (default: 30)
  - `match_thresh`: Threshold for matching detections to tracks (default: 0.9)
  - `aspect_ratio_thresh`: Aspect ratio threshold for matching (default: 2.0)
  - `min_box_area`: Minimum area of bounding box to consider (default: 500)
  - `mot20`: Use MOT20 matching strategy (default: false)

## 📊 Output

- Processed images and videos are saved to the `output/` directory by default
- Files are named based on input type with timestamps
- Real-time speed information is displayed on tracked objects when enabled
- FPS information is available when using the `--show-fps` flag

## 🔧 Speed Estimation Algorithm

The speed estimation system works by:

1. **Position Tracking**: Using the BYTE tracker to maintain consistent object IDs across frames
2. **Coordinate Logging**: Storing historical positions of tracked objects
3. **Distance Calculation**: Converting pixel distances to real-world distances using the `--pixel-distance` parameter
4. **Time Measurement**: Calculating time differences between positions
5. **Speed Calculation**: Computing speed in km/h using distance over time
6. **Smoothing**: Averaging recent speed measurements for stable display

The default pixel distance is 0.01 meters per pixel (1 cm/pixel), but this should be calibrated based on your camera setup and real-world measurements.

## 🐳 Docker Support

The project includes Docker support for easy deployment:

1. **Build the Docker image**:
   ```bash
   docker build -t yolov11-speed .
   ```

2. **Run with camera access** (Linux):
   ```bash
   docker run --rm -it --device=/dev/xdma0 --device=/dev/xdma_stat --device=/dev/hailo0 yolov11-speed
   ```

For detailed Docker instructions, see `Docker.md`.

## 📈 Performance Optimization

- The system is optimized for Hailo AI accelerators which provide high-performance inference
- Multi-threaded architecture separates preprocessing, inference, and post-processing
- Configurable batch size for optimization based on available resources
- Efficient tracking algorithm minimizes computational overhead

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- YOLOv11 object detection models
- BYTE (ByteTrack) multi-object tracking algorithm
- Hailo Technologies for AI acceleration
- OpenCV for computer vision operations