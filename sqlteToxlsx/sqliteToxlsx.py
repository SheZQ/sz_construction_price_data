import sqlite3
from openpyxl import Workbook
import os

def sqlite_to_xlsx(db_file, xlsx_file=None, specific_table=None):
    """
    将SQLite数据库转换为Excel文件
    :param db_file: SQLite数据库文件路径（同目录下直接传文件名）
    :param xlsx_file: 输出的Excel文件名，默认与数据库同名
    :param specific_table: 可选，指定要导出的单个表名，默认导出所有表
    :return: bool，成功返回True，失败返回False
    """
    # 检查数据库文件是否存在
    if not os.path.exists(db_file):
        print(f"【错误】未找到数据库文件：{db_file}")
        print(f"        当前脚本所在目录：{os.getcwd()}")
        print(f"        目录下的文件列表：{os.listdir('.')[:10]}")  # 打印前10个文件，避免刷屏
        return False

    # 初始化Excel工作簿
    wb = Workbook()
    wb.remove(wb.active)  # 删除默认的Sheet

    # 连接SQLite数据库
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        print(f"【成功】连接到数据库：{db_file}")

        # 获取要导出的表名列表
        if specific_table:
            # 检查指定表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (specific_table,))
            if not cursor.fetchone():
                print(f"【错误】数据库中不存在表：{specific_table}")
                # 打印数据库中所有表名，方便核对
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
                all_tables = [t[0] for t in cursor.fetchall()]
                print(f"        数据库中已存在的表：{all_tables}")
                return False
            table_names = [specific_table]
        else:
            # 查询所有表名
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            table_names = [t[0] for t in cursor.fetchall()]
            if not table_names:
                print("【提示】数据库中未找到任何表")
                return True  # 无表不算错误，返回成功

        # 遍历每个表并导出到Excel
        for table in table_names:
            print(f"【进度】正在导出表：{table}")
            # Excel工作表名最大31个字符，自动截断
            sheet_name = table[:31] if len(table) > 31 else table
            ws = wb.create_sheet(title=sheet_name)
            
            # 查询表的所有数据和列名
            cursor.execute(f"SELECT * FROM {table};")
            column_names = [desc[0] for desc in cursor.description]  # 表头
            rows = cursor.fetchall()  # 数据行

            # 写入表头和数据
            ws.append(column_names)
            for row in rows:
                ws.append(list(row))
            print(f"【完成】表 {table} 导出完成，共 {len(rows)} 行数据")

        # 设置默认Excel文件名
        if not xlsx_file:
            xlsx_file = os.path.splitext(db_file)[0] + ".xlsx"

        # 保存Excel文件
        wb.save(xlsx_file)
        print(f"\n【最终】所有表导出完成！Excel文件已保存为：{xlsx_file}")
        return True

    except sqlite3.Error as e:
        print(f"【数据库错误】{e}")
        return False
    except Exception as e:
        print(f"【未知错误】{e}")
        import traceback
        traceback.print_exc()  # 打印详细的异常栈，方便调试
        return False
    finally:
        # 关闭数据库连接
        if conn:
            conn.close()
            print("【提示】数据库连接已关闭")

if __name__ == "__main__":
    # ==================== 请修改这里的配置 ====================
    DB_FILE = "sz_price_info.db"  # 替换为你的SQLite数据库文件名（如mydata.db）
    XLSX_FILE = None  # 可选，自定义输出Excel名，如"output.xlsx"
    SPECIFIC_TABLE = None  # 可选，指定单个表名，如"users"
    # =========================================================

    # 执行转换
    print("开始执行SQLite转Excel操作...\n")
    result = sqlite_to_xlsx(DB_FILE, XLSX_FILE, SPECIFIC_TABLE)
    if result:
        print("\n操作成功完成！")
    else:
        print("\n操作失败，请根据以上错误信息排查问题！")