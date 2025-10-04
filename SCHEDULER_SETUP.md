# Hướng dẫn cấu hình Task Statistics Scheduler

## 🚀 Bắt đầu nhanh

### Bước 1: Cài đặt dependencies

```bash
pip install apscheduler
```

Hoặc chạy script tự động:

```bash
setup_scheduler.bat
```

### Bước 2: Khởi động server

```bash
python main.py
```

Server sẽ tự động khởi động scheduler và hiển thị:

```
✓ Statistics Scheduler loaded
✓ Statistics Scheduler started
  - Next midnight update: 2025-10-05 00:00:00
```

## 📅 Lịch trình cập nhật

Scheduler sẽ tự động cập nhật thống kê vào:

| Thời gian | Mục đích | Cron Expression |
|-----------|----------|-----------------|
| **00:00** (Nửa đêm) | Cập nhật ngày mới | `hour=0, minute=0` |
| **Mỗi 6 giờ** | Cập nhật định kỳ trong ngày | `hour='*/6'` |
| **23:55** (Cuối ngày) | Tổng kết ngày | `hour=23, minute=55` |

## 🔍 Kiểm tra hoạt động

### 1. Xem trạng thái scheduler

```bash
# Windows PowerShell
Invoke-WebRequest -Uri "http://localhost:5555/api/statistics/status" | Select-Object -Expand Content

# Hoặc dùng browser
http://localhost:5555/api/statistics/status
```

Kết quả:
```json
{
  "status": "running",
  "jobs": [
    {
      "id": "daily_stats_midnight",
      "name": "Daily Statistics Update (Midnight)",
      "next_run": "2025-10-05T00:00:00",
      "trigger": "cron[hour='0', minute='0']"
    }
  ]
}
```

### 2. Cập nhật thủ công (manual)

```bash
# Windows PowerShell
Invoke-WebRequest -Uri "http://localhost:5555/api/statistics/update" -Method POST

# Hoặc dùng curl
curl -X POST http://localhost:5555/api/statistics/update
```

### 3. Xem logs

Logs được ghi trong terminal khi chạy server:

```
2025-10-04 12:00:00 - StatisticsScheduler - INFO - Starting daily statistics update for 2025-10-04
2025-10-04 12:00:01 - StatisticsScheduler - INFO - ✓ Daily statistics updated successfully
2025-10-04 12:00:01 - StatisticsScheduler - INFO -   - Total tasks: 150
2025-10-04 12:00:01 - StatisticsScheduler - INFO -   - Completed: 145
```

## 💾 Database

Thống kê được lưu trong file SQLite:

```
logs/statistics.db
```

Bạn có thể xem dữ liệu bằng SQLite browser hoặc Python:

```python
import sqlite3
conn = sqlite3.connect('logs/statistics.db')
cursor = conn.cursor()
cursor.execute('SELECT * FROM daily_statistics ORDER BY date DESC LIMIT 10')
for row in cursor.fetchall():
    print(row)
conn.close()
```

## ⚙️ Tùy chỉnh

### Thay đổi lịch trình

Chỉnh sửa file `service/statistics/scheduler.py`:

```python
# Ví dụ: Cập nhật mỗi giờ
self.scheduler.add_job(
    self.update_daily_statistics,
    trigger=CronTrigger(hour='*'),  # Mỗi giờ
    id='hourly_update',
    name='Hourly Statistics Update'
)

# Ví dụ: Cập nhật vào 8h sáng và 5h chiều
self.scheduler.add_job(
    self.update_daily_statistics,
    trigger=CronTrigger(hour='8,17'),  # 8AM và 5PM
    id='business_hours',
    name='Business Hours Update'
)
```

### Thay đổi thời gian cụ thể

```python
# Cập nhật vào 7h30 sáng mỗi ngày
CronTrigger(hour=7, minute=30)

# Cập nhật vào 12h trưa các ngày thứ 2, 3, 5
CronTrigger(hour=12, minute=0, day_of_week='mon,wed,fri')

# Cập nhật ngày đầu tháng
CronTrigger(day=1, hour=0, minute=0)
```

## 🎯 Use Cases

### 1. Cập nhật thường xuyên (Real-time)

```python
# Mỗi 30 phút
CronTrigger(minute='*/30')
```

### 2. Chỉ cập nhật giờ làm việc

```python
# 8AM-6PM, Thứ 2-6
CronTrigger(hour='8-18', day_of_week='mon-fri')
```

### 3. Cập nhật cuối tuần

```python
# Chủ nhật 11h đêm
CronTrigger(hour=23, day_of_week='sun')
```

## 🔧 Troubleshooting

### Lỗi: APScheduler not found

```bash
pip install apscheduler
```

### Scheduler không chạy

1. Kiểm tra logs khi khởi động server
2. Kiểm tra API status:
   ```bash
   curl http://localhost:5555/api/statistics/status
   ```

### Database không cập nhật

1. Kiểm tra quyền ghi folder `logs/`
2. Chạy manual update:
   ```bash
   curl -X POST http://localhost:5555/api/statistics/update
   ```
3. Xem logs để biết lỗi chi tiết

### Muốn tắt scheduler tạm thời

Trong `main.py`, comment dòng:

```python
# statistics_scheduler.start()
```

## 📊 Ví dụ output

Khi scheduler chạy thành công:

```
2025-10-04 00:00:00 - StatisticsScheduler - INFO - Starting daily statistics update for 2025-10-04
2025-10-04 00:00:01 - StatisticsScheduler - INFO - ✓ Daily statistics updated successfully for 2025-10-04
2025-10-04 00:00:01 - StatisticsScheduler - INFO -   - Total tasks: 247
2025-10-04 00:00:01 - StatisticsScheduler - INFO -   - Completed: 241
2025-10-04 00:00:01 - StatisticsScheduler - INFO -   - Failed: 6
2025-10-04 00:00:01 - StatisticsScheduler - INFO -   - Cards detected: 482
```

## 📞 Support

Nếu gặp vấn đề, kiểm tra:
1. ✅ APScheduler đã cài đặt: `pip list | findstr apscheduler`
2. ✅ File logs/statistics.db tồn tại và có quyền ghi
3. ✅ Server chạy trên port 5555: `netstat -ano | findstr :5555`
4. ✅ Logs trong terminal có thông báo lỗi không
