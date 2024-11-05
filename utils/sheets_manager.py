from google.oauth2.service_account import Credentials
import gspread

scopes = ["https://www.googleapis.com/auth/spreadsheets"]

class SheetsManager:
    def __init__(self, cred_path, sheet_id):
        try:
            creds = Credentials.from_service_account_file(cred_path, scopes=scopes)
            client = gspread.authorize(creds)

            self.sheet = client.open_by_key(sheet_id)

        except gspread.exceptions.APIError as e:
            print(f"APIError: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

    def mutual_sympathy(self, account, username, city):
        print(self.sheet)
        print(account, username, city)
        worksheet = self.sheet.sheet1

        free_row = 1
        while True:
            row = worksheet.row_values(free_row)

            all_strings_empty = all(s.strip() == '' for s in row)

            if all_strings_empty:
                break
            free_row += 1


        worksheet.update_cell(free_row, 1, account) # Column A
        worksheet.update_cell(free_row, 2, username) # Column B
        worksheet.update_cell(free_row, 3, city) # Column C
