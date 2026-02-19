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

# -------------------------
# 事前定義（効率化）
# -------------------------
DICE_PATTERN = re.compile(r"\b(\d+)d(\d+)\b")
COMPARE_PATTERN = re.compile(r"(>=|<=|==|>|<|=)")

allowed_operators = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg
}

compare_ops = {
    "=": operator.eq,
    "==": operator.eq,
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le
}

# -------------------------
# 安全計算
# -------------------------
def safe_eval(expr):
    def eval_node(node):
        if isinstance(node, ast.Constant):  # Python3.8+
            return node.value
        if isinstance(node, ast.Num):  # 旧互換
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

# -------------------------
# メイン処理
# -------------------------
@bot.event
async def on_message(message):
    if message.author.bot or not message.content.startswith("!r"):
        return

    raw = message.content[2:].strip()

    if not raw:
        expr = "1d100"
        comment = ""
    else:
        raw = raw.replace("　", " ")
        parts = raw.split(" ", 1)
        expr = parts[0]
        comment = parts[1] if len(parts) > 1 else ""

    try:
        # -------------------------
        # 比較処理
        # -------------------------
        comparison_match = COMPARE_PATTERN.search(expr)
        comparator = None
        compare_value = None

        if comparison_match:
            comparator = comparison_match.group()
            left, right = expr.split(comparator, 1)
            compare_value = safe_eval(right)
            expr = left.strip()

        # -------------------------
        # ダイス展開
        # -------------------------
        display_parts = []
        calc_parts = []
        last_index = 0

        for match in DICE_PATTERN.finditer(expr):
            start, end = match.span()
            n, m = map(int, match.groups())

            calc_parts.append(expr[last_index:start])
            display_parts.append(expr[last_index:start])

            rolls = [random.randint(1, m) for _ in range(n)]
            total = sum(rolls)
            roll_text = "+".join(map(str, rolls))

            calc_parts.append(str(total))
            display_parts.append(f"{n}d{m}({roll_text})")

            last_index = end

        calc_parts.append(expr[last_index:])
        display_parts.append(expr[last_index:])

        calc_expr = "".join(calc_parts)
        display_expr = "".join(display_parts)

        # -------------------------
        # 計算
        # -------------------------
        result = round(safe_eval(calc_expr), 3)
        if result == int(result):
            result = int(result)

        # -------------------------
        # 比較判定
        # -------------------------
        compare_text = ""
        if comparator:
            success = compare_ops[comparator](result, compare_value)
            compare_text = f"\nResult：{'Success' if success else 'Fail'}"

        # -------------------------
        # 出力
        # -------------------------
        if comment:
            output = (
                f"{message.author.mention}\n"
                f"{comment}：{display_expr}\n"
                f"Total：**{result}**{compare_text}"
            )
        else:
            output = (
                f"{message.author.mention}\n"
                f"{display_expr}\n"
                f"Total：**{result}**{compare_text}"
            )

        await message.channel.send(output)

    except Exception as e:
        await message.channel.send(f"Error: {e}")

bot.run(TOKEN)
