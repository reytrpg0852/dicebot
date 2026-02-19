import discord
import random
import re
import ast
import operator
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

allowed_operators = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg
}

def safe_eval(expr):
    def eval_node(node):
        if isinstance(node, ast.Num):
            return node.n
        if isinstance(node, ast.UnaryOp):
            return allowed_operators[type(node.op)](eval_node(node.operand))
        if isinstance(node, ast.BinOp):
            return allowed_operators[type(node.op)](
                eval_node(node.left),
                eval_node(node.right)
            )
        raise ValueError("Invalid expression")

    node = ast.parse(expr, mode="eval").body
    return eval_node(node)

def roll_dice(n, m):
    if n <= 0 or m <= 0:
        raise ValueError("n and m must be positive")
    if n > 100:
        raise ValueError("n must be <= 100")
    if m > 1000:
        raise ValueError("m must be <= 1000")
    return [random.randint(1, int(m)) for _ in range(int(n))]

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if not message.content.startswith("!r"):
        return

    raw = message.content[2:].strip()

    if raw == "":
        expr = "1d100"
        comment = ""
    else:
        raw = raw.replace("　", " ")
        parts = raw.split(" ", 1)
        expr = parts[0]
        comment = parts[1] if len(parts) > 1 else ""

    try:
        # -----------------------------
        # 比較処理（安全版）
        # -----------------------------
        comparison_match = re.search(r"(>=|<=|==|>|<|=)", expr)
        comparator = None
        compare_value = None

        if comparison_match:
            comparator = comparison_match.group()
            left, right = expr.split(comparator, 1)
            compare_value = safe_eval(right)
            expr = left.strip()

        display_expr = expr
        dice_pattern = r"(\d+)d(\d+)"

        # -----------------------------
        # ダイス展開（位置同期修正版）
        # -----------------------------
        while True:
            match = re.search(dice_pattern, expr)
            if not match:
                break

            n, m = map(int, match.groups())
            rolls = roll_dice(n, m)
            total = sum(rolls)
            roll_text = "+".join(str(r) for r in rolls)

            # 計算式置換
            expr = expr[:match.start()] + str(total) + expr[match.end():]

            # 表示式も同じ位置で置換
            display_expr = (
                display_expr[:match.start()] +
                f"{n}d{m}({roll_text})" +
                display_expr[match.end():]
            )

        # -----------------------------
        # 計算
        # -----------------------------
        result = round(safe_eval(expr), 3)

        if result == int(result):
            result = int(result)

        # -----------------------------
        # 比較判定
        # -----------------------------
        compare_text = ""
        if comparator:
            if comparator in ["=", "=="]:
                success = result == compare_value
            elif comparator == ">":
                success = result > compare_value
            elif comparator == "<":
                success = result < compare_value
            elif comparator == ">=":
                success = result >= compare_value
            elif comparator == "<=":
                success = result <= compare_value

            compare_text = f"\nResult：{'Success' if success else 'Fail'}"

        # -----------------------------
        # 出力
        # -----------------------------
        if comment:
            output = f"{comment}：{display_expr}\nTotal：**{result}**{compare_text}"
        else:
            output = f"{display_expr}\nTotal：**{result}**{compare_text}"

        await message.channel.send(output)

    except Exception as e:
        await message.channel.send(f"Error: {e}")

bot.run(TOKEN)
