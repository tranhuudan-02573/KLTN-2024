import requests
import concurrent.futures

# URL của API
url = "https://dkmh.hcmuaf.edu.vn/api/dkmh/w-xulydkmhsinhvien"

# Headers bao gồm Bearer Token
headers = {
    "Authorization": "Bearer eyJhbGciOiJodHRwOi8vd3d3LnczLm9yZy8yMDAxLzA0L3htbGRzaWctbW9yZSNobWFjLXNoYTI1NiIsInR5cCI6IkpXVCJ9.eyJodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9uYW1laWRlbnRpZmllciI6Ii03Njk2MTI5MDE0MTUzNTY5MjI1IiwiaHR0cDovL3NjaGVtYXMueG1sc29hcC5vcmcvd3MvMjAwNS8wNS9pZGVudGl0eS9jbGFpbXMvbmFtZSI6IjIwMTMwMjE4IiwiaHR0cDovL3NjaGVtYXMubWljcm9zb2Z0LmNvbS9hY2Nlc3Njb250cm9sc2VydmljZS8yMDEwLzA3L2NsYWltcy9pZGVudGl0eXByb3ZpZGVyIjoiQVNQLk5FVCBJZGVudGl0eSIsIkFzcE5ldC5JZGVudGl0eS5TZWN1cml0eVN0YW1wIjoiN2FiODJkNDQtMzVjMC00YmU2LTgxYjAtYmMzNjI1N2NiZDQ1IiwiaHR0cDovL3NjaGVtYXMubWljcm9zb2Z0LmNvbS93cy8yMDA4LzA2L2lkZW50aXR5L2NsYWltcy9yb2xlIjoiU0lOSFZJRU4iLCJzZXNzaW9uIjoiLTYzNzQ2NzkzNTU2MDM5NTc5MjIiLCJuYW1lIjoiVHLhuqduIEjhu691IETDom4iLCJwYXNzdHlwZSI6IjAiLCJ1Y3YiOiIxMTAzNzk0NjMyIiwicHJpbmNpcGFsIjoiMjAxMzAyMThAc3QuaGNtdWFmLmVkdS52biIsIndjZiI6IjAiLCJuYmYiOjE3MjM0MzUzMTcsImV4cCI6MTcyMzQzNzExNywiaXNzIjoiZWR1c29mdCIsImF1ZCI6ImFsbCJ9.ltsG6mBVUA2vAhEjyKcs6UBK3Yaepyyd9ugyU8XfxRo",
    "Content-Type": "application/json"
}

# Body của request
body = {
    "filter": {
        "id_to_hoc": "-5264587219105252719",
        "is_checked": True,
        "sv_nganh": 1
    }
}

# Hàm gửi request
def send_request():
    try:
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()  # Sẽ ném exception nếu mã trạng thái không phải 2xx
        print("Request thành công!")
        print("Status Code:", response.status_code)
        print("Response Body:", response.json())
    except requests.RequestException as e:
        print(f"Đã xảy ra lỗi: {e}")

# Số lượng kết nối đồng thời
num_connections = 10

# Gửi request đồng thời
with concurrent.futures.ThreadPoolExecutor(max_workers=num_connections) as executor:
    futures = [executor.submit(send_request) for _ in range(num_connections)]
    # Đợi tất cả các futures hoàn thành
    for future in concurrent.futures.as_completed(futures):
        future.result()  # Có thể sử dụng để kiểm tra lỗi
