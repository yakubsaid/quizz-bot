# main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import json
import random
import string
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)

# Bot configuration
BOT_TOKEN = "8067408775:AAH7dq5lq-tJbKq6ElQL9JI-RJ67_mbZENM"  # Replace with your bot token
OWNER_ID = 5479445322  # Replace with owner's Telegram ID

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# States for FSM
class QuizCreation(StatesGroup):
    waiting_for_quiz_name = State()
    waiting_for_question_count = State()
    waiting_for_question = State()
    waiting_for_variants = State()
    waiting_for_correct_answer = State()

class QuizTaking(StatesGroup):
    waiting_for_name = State()
    taking_quiz = State()

# Data storage (in production, use a database)
quizzes = {}
quiz_results = {}
users = {}

class QuizManager:
    @staticmethod
    def generate_quiz_code():
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    @staticmethod
    def save_quiz(quiz_data):
        code = QuizManager.generate_quiz_code()
        while code in quizzes:
            code = QuizManager.generate_quiz_code()
        quizzes[code] = quiz_data
        return code
    
    @staticmethod
    def get_quiz(code):
        return quizzes.get(code)
    
    @staticmethod
    def save_result(quiz_code, user_name, user_id, username, score, total, answers):
        if quiz_code not in quiz_results:
            quiz_results[quiz_code] = []
        
        result = {
            'user_name': user_name,
            'user_id': user_id,
            'username': username,
            'score': score,
            'total': total,
            'answers': answers,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        quiz_results[quiz_code].append(result)
        
        # Save user info
        users[user_id] = {
            'name': user_name,
            'username': username,
            'last_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

# Owner keyboard
def get_owner_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Test yaratish", callback_data="create_quiz")],
        [InlineKeyboardButton(text="📊 Natijalarni ko'rish", callback_data="view_results")],
        [InlineKeyboardButton(text="👥 Foydalanuvchilarni ko'rish", callback_data="view_users")],
        [InlineKeyboardButton(text="🗂️ Testlarim", callback_data="my_quizzes")]
    ])
    return keyboard

# Quiz selection keyboard for results
def get_quiz_selection_keyboard():
    keyboard = []
    for code, quiz in quizzes.items():
        keyboard.append([InlineKeyboardButton(
            text=f"🎯 {quiz['name']} ({code})",
            callback_data=f"quiz_results_{code}"
        )])
    
    if not keyboard:
        return None
    
    keyboard.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Start command
@dp.message(Command("start"))
async def start_command(message: types.Message):
    if message.from_user.id == OWNER_ID:
        await message.answer(
            "🎮 Test Botga Xush kelibsiz!\n\n"
            "Siz egasiz. Qanday ish qilmoqchisiz:",
            reply_markup=get_owner_keyboard()
        )
    else:
        await message.answer(
            "🎮 Test Botga Xush kelibsiz!\n\n"
            "Test olish uchun quyidagi buyruqni ishlating:\n"
            "/quiz [CODE]\n\n"
            "Misol: /quiz ABC123\n\n"
            "Test yaratuvchisidan test kodini oling!"
        )

# Quiz command for users
@dp.message(Command("quiz"))
async def quiz_command(message: types.Message, state: FSMContext):
    if message.from_user.id == OWNER_ID:
        await message.answer("❌ Egalar test ololmaydi. Testlarni boshqarish uchun menyudan foydalaning.")
        return
    
    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ Iltimos, test kodini taqdim eting.\nMisol: /quiz ABC123")
        return
    
    quiz_code = args[1].upper()
    quiz = QuizManager.get_quiz(quiz_code)
    
    if not quiz:
        await message.answer("❌ Test topilmadi. Iltimos, kodni tekshiring.")
        return
    
    await state.update_data(quiz_code=quiz_code, quiz=quiz)
    await message.answer(
        f"🎯 Testga xush kelibsiz: {quiz['name']}\n\n"
        f"📝 Savollar: {len(quiz['questions'])}\n\n"
        "Iltimos, to'liq ismingizni kiriting:"
    )
    await state.set_state(QuizTaking.waiting_for_name)

# Handle owner callbacks
@dp.callback_query(lambda c: c.from_user.id == OWNER_ID)
async def handle_owner_callbacks(callback: CallbackQuery, state: FSMContext):
    if callback.data == "create_quiz":
        await callback.message.edit_text(
            "📝 Yangi test yaratilyapti...\n\n"
            "Iltimos, test nomini kiriting:"
        )
        await state.set_state(QuizCreation.waiting_for_quiz_name)
    
    elif callback.data == "view_results":
        quiz_keyboard = get_quiz_selection_keyboard()
        if quiz_keyboard:
            await callback.message.edit_text(
                "📊 Natijalarni ko'rish uchun testni tanlang:",
                reply_markup=quiz_keyboard
            )
        else:
            await callback.message.edit_text(
                "📊 Hech qanday test topilmadi.\n\n"
                "Avval test yarating!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")]
                ])
            )
    
    elif callback.data == "view_users":
        if users:
            user_list = "👥 Ro'yxatdan o'tgan foydalanuvchilar:\n\n"
            for user_id, user_info in users.items():
                user_list += f"👤 {user_info['name']}\n"
                if user_info.get('username'):
                    user_list += f"📱 @{user_info['username']}\n"
                else:
                    user_list += f"📱 Hech qanday username yo'q\n"
                user_list += f"🆔 ID: {user_id}\n"
                user_list += f"📅 Oxirgi ko'rish: {user_info['last_seen']}\n\n"
        else:
            user_list = "👥 Hech qanday foydalanuvchi test o'tkazmagan."
        
        await callback.message.edit_text(
            user_list,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")]
            ])
        )
    
    elif callback.data == "my_quizzes":
        if quizzes:
            quiz_list = "🗂️ Savollaringiz:\n\n"
            for code, quiz in quizzes.items():
                quiz_list += f"🎯 {quiz['name']}\n"
                quiz_list += f"🔑 Kod: {code}\n"
                quiz_list += f"❓ Savollar: {len(quiz['questions'])}\n\n"
        else:
            quiz_list = "🗂️ Hech qanday test yaratilmagan."
        
        await callback.message.edit_text(
            quiz_list,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")]
            ])
        )
    
    elif callback.data == "back_to_menu":
        await callback.message.edit_text(
            "🎮 Test botga xush kelibsiz!\n\n"
            "Siz egasiz. Qanday ish qilmoqchisiz:",
            reply_markup=get_owner_keyboard()
        )
    
    elif callback.data.startswith("quiz_results_"):
        quiz_code = callback.data.replace("quiz_results_", "")
        results = quiz_results.get(quiz_code, [])
        quiz = quizzes.get(quiz_code)
        
        if results:
            results_text = f"📊 Natijalar uchun: {quiz['name']}\n\n"
            for i, result in enumerate(results, 1):
                results_text += f"{i}. {result['user_name']}\n"
                if result.get('username'):
                    results_text += f"   @{result['username']}\n"
                else:
                    results_text += f"   Hech qanday username yo'q\n"
                results_text += f"   ID: {result['user_id']}\n"
                results_text += f"   Ball: {result['score']}/{result['total']}\n"
                results_text += f"   Sana: {result['date']}\n\n"
        else:
            results_text = f"📊 Natijalar uchun: {quiz['name']}"
        
        await callback.message.edit_text(
            results_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="view_results")]
            ])
        )
    
    await callback.answer()

# Handle quiz creation states
@dp.message(QuizCreation.waiting_for_quiz_name)
async def process_quiz_name(message: types.Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    
    await state.update_data(quiz_name=message.text)
    await message.answer(
        f"✅ Test nomi: {message.text}\n\n"
        "Qancha savol qo'shmoqchisiz?"
    )
    await state.set_state(QuizCreation.waiting_for_question_count)

@dp.message(QuizCreation.waiting_for_question_count)
async def process_question_count(message: types.Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    
    try:
        count = int(message.text)
        if count <= 0:
            await message.answer("❌ Iltimos, musbat raqam kiriting.")
            return
    except ValueError:
        await message.answer("❌ Iltimos, to'g'ri raqam kiriting.")
        return
    
    await state.update_data(
        question_count=count,
        current_question=1,
        questions=[]
    )
    await message.answer(
        f"📝 1-savol {count} dan:\n\n"
        "Iltimos, savolni kiriting:"
    )
    await state.set_state(QuizCreation.waiting_for_question)

@dp.message(QuizCreation.waiting_for_question)
async def process_question(message: types.Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    
    data = await state.get_data()
    await state.update_data(current_question_text=message.text)
    await message.answer(
        f"Savol: {message.text}\n\n"
        "Endi 3 ta javob variantini kiriting, har birini alohida xabarda.\n"
        "Variant 1 ni yuboring:"
    )
    await state.update_data(variants=[], variant_count=1)
    await state.set_state(QuizCreation.waiting_for_variants)

@dp.message(QuizCreation.waiting_for_variants)
async def process_variants(message: types.Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    
    data = await state.get_data()
    variants = data.get('variants', [])
    variants.append(message.text)
    variant_count = data.get('variant_count', 1)
    
    if variant_count < 3:
        await state.update_data(variants=variants, variant_count=variant_count + 1)
        await message.answer(f"✅ Variant {variant_count}: {message.text}\n\nVariant {variant_count + 1} ni yuboring:")
    else:
        await state.update_data(variants=variants)
        variant_text = "\n".join([f"{i+1}. {v}" for i, v in enumerate(variants)])
        await message.answer(
            f"✅ Hamma variantlar qo'shildi:\n\n{variant_text}\n\n"
            "Qaysi javob to'g'ri? (Enter 1, 2, yoki 3):"
        )
        await state.set_state(QuizCreation.waiting_for_correct_answer)

@dp.message(QuizCreation.waiting_for_correct_answer)
async def process_correct_answer(message: types.Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    
    try:
        correct_answer = int(message.text)
        if correct_answer not in [1, 2, 3]:
            await message.answer("❌ Iltimos, 1, 2, yoki 3 ni kiriting.")
            return
    except ValueError:
        await message.answer("❌ Iltimos, to'g'ri raqam kiriting (1, 2, yoki 3).")
        return
    
    data = await state.get_data()
    questions = data.get('questions', [])
    
    question_data = {
        'question': data['current_question_text'],
        'variants': data['variants'],
        'correct_answer': correct_answer - 1  # Convert to 0-based index
    }
    questions.append(question_data)
    
    current_question = data['current_question']
    question_count = data['question_count']
    
    if current_question < question_count:
        await state.update_data(
            questions=questions,
            current_question=current_question + 1
        )
        await message.answer(
            f"✅ Savol {current_question} saqlangan!\n\n"
            f"📝 {question_count} dan {current_question + 1}-savol:\n\n"
            "Iltimos, savolni kiriting:"
        )
        await state.set_state(QuizCreation.waiting_for_question)
    else:
        # Quiz creation complete
        quiz_data = {
            'name': data['quiz_name'],
            'questions': questions,
            'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        quiz_code = QuizManager.save_quiz(quiz_data)
        
        await message.answer(
            f"🎉 Test yaratildi muvaffaqiyatli!\n\n"
            f"📝 Test: {quiz_data['name']}\n"
            f"🔑 Kod: {quiz_code}\n"
            f"❓ Savollar: {len(questions)}\n\n"
            f"Ushbu kodni foydalanuvchilar bilan ulashing, ular testni o'tishlari uchun:\n"
            f"/quiz {quiz_code}",
            reply_markup=get_owner_keyboard()
        )
        await state.clear()

# Handle quiz taking states
@dp.message(QuizTaking.waiting_for_name)
async def process_user_name(message: types.Message, state: FSMContext):
    if message.from_user.id == OWNER_ID:
        return
    
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❌ Iltimos, to'liq ismingizni kiriting (kamida 2 ta belgi).")
        return
    
    data = await state.get_data()
    await state.update_data(
        user_name=name,
        current_question=0,
        answers=[],
        score=0
    )
    
    quiz = data['quiz']
    question = quiz['questions'][0]
    
    # Create answer buttons
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"A) {question['variants'][0]}", callback_data="answer_0")],
        [InlineKeyboardButton(text=f"B) {question['variants'][1]}", callback_data="answer_1")],
        [InlineKeyboardButton(text=f"C) {question['variants'][2]}", callback_data="answer_2")]
    ])
    
    await message.answer(
        f"👋 Salom, {name}!\n\n"
        f"🎯 Test: {quiz['name']}\n\n"
        f"📝 1-savol {len(quiz['questions'])} dan:\n\n"
        f"{question['question']}",
        reply_markup=keyboard
    )
    await state.set_state(QuizTaking.taking_quiz)

# Handle quiz answers
@dp.callback_query(lambda c: c.data.startswith("answer_"))
async def handle_quiz_answers(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id == OWNER_ID:
        await callback.answer("❌ Ega test yecha olmaydi.")
        return
    
    data = await state.get_data()
    quiz = data['quiz']
    current_question = data['current_question']
    answers = data.get('answers', [])
    score = data.get('score', 0)
    
    # Get selected answer
    selected_answer = int(callback.data.split('_')[1])
    correct_answer = quiz['questions'][current_question]['correct_answer']
    
    # Check if answer is correct
    is_correct = selected_answer == correct_answer
    if is_correct:
        score += 1
    
    answers.append({
        'question': quiz['questions'][current_question]['question'],
        'selected': selected_answer,
        'correct': correct_answer,
        'is_correct': is_correct
    })
    
    current_question += 1
    
    if current_question < len(quiz['questions']):
        # Next question
        question = quiz['questions'][current_question]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"A) {question['variants'][0]}", callback_data="answer_0")],
            [InlineKeyboardButton(text=f"B) {question['variants'][1]}", callback_data="answer_1")],
            [InlineKeyboardButton(text=f"C) {question['variants'][2]}", callback_data="answer_2")]
        ])
        
        await callback.message.edit_text(
            f"📝 Question {current_question + 1} of {len(quiz['questions'])}:\n\n"
            f"{question['question']}",
            reply_markup=keyboard
        )
        
        await state.update_data(
            current_question=current_question,
            answers=answers,
            score=score
        )
    else:
        # Quiz finished
        quiz_code = data['quiz_code']
        user_name = data['user_name']
        total_questions = len(quiz['questions'])
        
        # Save result
        QuizManager.save_result(
            quiz_code, user_name, callback.from_user.id, 
            callback.from_user.username,
            score, total_questions, answers
        )
        
        # Show results to user
        result_text = f"🎉 Test tugatildi!\n\n"
        result_text += f"👤 Ism: {user_name}\n"
        result_text += f"📊 Ball: {score}/{total_questions}\n"
        result_text += f"📈 Foiz: {round(score/total_questions*100, 1)}%\n\n"
        
        if score == total_questions:
            result_text += "🏆 Mukammal ball! Tabriklaymiz!"
        elif score >= total_questions * 0.8:
            result_text += "🎯 Ajoyib ish! Zo'r natija!"
        elif score >= total_questions * 0.6:
            result_text += "👍 Yaxshi ish! Davom eting!"
        else:
            result_text += "📚 O'qishni davom ettiring va qayta urinib ko'ring!"
        
        await callback.message.edit_text(result_text)
        
        # Send results to owner
        owner_text = f"📊 Yangi Test Natijasi!\n\n"
        owner_text += f"🎯 Test: {quiz['name']}\n"
        owner_text += f"👤 Talaba: {user_name}\n"
        if callback.from_user.username:
            owner_text += f"📱 Username: @{callback.from_user.username}\n"
        else:
            owner_text += f"📱 No username\n"
        owner_text += f"🆔 ID: {callback.from_user.id}\n"
        owner_text += f"📊 Ball: {score}/{total_questions} ({round(score/total_questions*100, 1)}%)\n"
        owner_text += f"📅 Sana: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        await bot.send_message(OWNER_ID, owner_text)
        await state.clear()
    
    await callback.answer()

# Main function
async def main():
    print("🤖 Quiz Bot starting...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
