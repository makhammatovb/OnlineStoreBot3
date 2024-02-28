from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.types import InputMediaPhoto


from config import DB_NAME
from keyboards.admin_inline_keyboards import categories_kb_4_products, update_products_kb, delete_products_kb, \
    make_product_kb, get_products_kb
from keyboards.client_keyboards import get_next_prev_keyboard, next_prev_kb
from states.admin_states import ProductsStates
from states.client_states import ShowStates
from utils.database import Database


product_router = Router()
db = Database(DB_NAME)


@product_router.message(Command('add_product'))
async def add_product_handler(message: Message, state: FSMContext):
    await state.set_state(ProductsStates.add_SelectCategoryProdState)
    await message.answer(
        text="Please choose a category which you want to add product:",
        reply_markup=categories_kb_4_products()
    )


@product_router.callback_query(ProductsStates.add_SelectCategoryProdState)
async def add_product_category_handler(query: CallbackQuery, state: FSMContext):
    await state.update_data(product_category=query.data)
    await state.set_state(ProductsStates.add_TitleProdState)
    await query.message.answer("Please, send a title for your product...")
    await query.message.delete()


@product_router.message(ProductsStates.add_TitleProdState)
async def add_product_title_handler(message: Message, state: FSMContext):
    if message.text:
        await state.update_data(product_title=message.text)
        await state.set_state(ProductsStates.add_TextProdState)
        await message.answer("Please, send full description for your product...")
    else:
        await message.answer("Please, send only text...")


@product_router.message(ProductsStates.add_TextProdState)
async def add_product_text_handler(message: Message, state: FSMContext):
    if message.text:
        await state.update_data(product_text=message.text)
        await state.set_state(ProductsStates.add_ImageProdState)
        await message.answer("Please, send image of your product...")
    else:
        await message.answer("Please, send only image...")


@product_router.message(ProductsStates.add_ImageProdState)
async def add_product_image_handler(message: Message, state: FSMContext):
    if message.photo:
        await state.update_data(product_image=message.photo[-1].file_id)
        await state.set_state(ProductsStates.add_PriceProdState)
        await message.answer("Please, send price of your product...")
    else:
        await message.answer("Please, send only text...")


@product_router.message(ProductsStates.add_PriceProdState)
async def add_product_price_handler(message: Message, state: FSMContext):
    if message.text.isdigit():
        await state.update_data(product_price=int(message.text))
        await state.set_state(ProductsStates.add_PhoneProdState)
        await message.answer("Please, send your phone number to contact with you...")
    else:
        await message.answer("Please, send only numbers...")


@product_router.message(ProductsStates.add_PhoneProdState)
async def add_product_contact_handler(message: Message, state: FSMContext):
    if message.text or message.contact:
        phone = message.text if message.text else message.contact.phone_number
        all_data = await state.get_data()
        cat_id = all_data.get('product_category')
        result = db.add_product(title=all_data.get('product_title'),
                                text=all_data.get('product_text'),
                                image=all_data.get('product_image'),
                                price=all_data.get('product_price'),
                                phone=phone,
                                cat_id=cat_id,
                                u_id=message.from_user.id)
        if result:
            await message.answer("Your product has been successfully added!")
            product = db.get_my_last_product(message.from_user.id)
            await message.answer_photo(
                    photo=product[3],
                    caption=f"{product[1]}\n\n {product[2]}\n\n "
                        f"Price: {product[4]}\n\n "
                        f"Contact: {product[-1]}"
                )
        else:
            await message.answer("Something went wrong, please try again")
        await state.clear()
    else:
        await message.answer("Please send a valid phone number...")


@product_router.callback_query()
async def category_product_handler(query: CallbackQuery, state: FSMContext):
    try:
        category_id = query.data
        await state.update_data(product_category = category_id)
    except Exception as e:
        print(f"Exception: {e}")
        await query.answer("An error occurred")

@product_router.message(Command('edit_product'))
async def edit_product_handler(message: Message, state: FSMContext):
    await state.set_state(ProductsStates.startEditProductState)
    await message.answer(
        text="Select product's category which you want change:",
        reply_markup=update_products_kb()
    )


@product_router.callback_query()
async def category_select_handler(query: CallbackQuery, state: FSMContext):
    category_id = query.data
    products = db.get_products_by_category(category_id)
    if products:
        await query.answer()
        message_text = "Selected products:\n\n"
        for product in products:
            product_info = f"Title: {product['product_title']}\n" \
                           f"Text: {product['product_text']}\n" \
                           f"Image: {product['product_image']}\n" \
                           f"Price: {product['product_price']}\n" \
                           f"Phone: {product['product_phone']}\n\n"
            message_text += product_info
        await query.message.answer(message_text)
    else:
        await query.answer("No products found in the selected category...")
    await state.update_data(selected_category=category_id)



@product_router.message(Command('del_product'))
async def del_product_handler(message: Message, state=FSMContext):
    await state.set_state(ProductsStates.startDelProductState)
    await message.answer(
        text="Select category which you want to change:",
        reply_markup=delete_products_kb()
    )

@product_router.callback_query(ProductsStates.startDelProductState)
async def select_category_del_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProductsStates.finishDelProductState)
    await state.update_data(cat_name=callback.data)
    await callback.message.edit_text(
        text=f"Do you want to delete category's product \"{callback.data}\":",
        reply_markup=make_product_kb()
    )

@product_router.callback_query(ProductsStates.finishDelProductState)
async def remove_product_handler(callback: CallbackQuery, state: FSMContext):
    if callback.data == 'YES':
        all_data = await state.get_data()
        if db.delete_product(all_data.get('cat_name')):
            await callback.message.answer("Category's products successfully deleted!")
            await callback.message.delete()
            await state.clear()
        else:
            await callback.message.answer(
                f"Something went wrong!"
                f"Try again later or click /cancel for cancel process!"
            )
    else:
        await state.clear()
        await callback.message.answer('Process canceled!')
        await callback.message.delete()



# @product_router.message(Command('products'))
# async def product_list_handler(message: Message):
#     await message.answer(
#         text="All products:",
#         reply_markup=get_products_kb()
#     )


@product_router.message(Command('products'))
async def products_handler(message: Message, state: FSMContext):
    products = db.get_all_products()
    print(products)
    if products:
        if len(products) == 1:
            product = products[0]
            await message.answer_photo(
                photo=product[3],
                caption=f"<b>{product[1]}</b>\n\n<b>{product[2]}</b>\n\nPrice: {product[4]}\n\nContact: {product[-1]}"
            )
        else:
            await state.set_state(ShowStates.showProductState)
            await state.update_data(index=0)
            await state.update_data(count=len(products))
            await state.update_data(products=products)
            product = products[0]
            await message.answer_photo(
                photo=product[3],
                caption=f"<b>{product[1]}</b>\n\n<b>{product[2]}</b>\n\nPrice: {product[4]}\n\nContact: {product[-1]}",
                reply_markup=next_prev_kb,
                parse_mode="HTML"
            )
    else:
        await message.answer("No products found.")

@product_router.callback_query(ShowStates.showProductState)
async def show_product_callback_query(query: CallbackQuery, state: FSMContext):
        all_data = await state.get_data()
        index = all_data["index"]
        count = all_data["count"]
        products = all_data["products"]

        if query.data == "next":
            if index == count - 1:
                index = 0
            else:
                index += 1
        else:
            if index == 0:
                index = count - 1
            else:
                index -= 1
        await state.update_data(index=index)
        await query.message.edit_media(
                media=InputMediaPhoto(
                    media=products[index][3],
                    caption=f"<b>{products[index][1]}</b>\n\n<b>{products[index][2]}</b>\n\nPrice: {products[index][4]}\n\nContact: {products[index][-1]}",
                    parse_mode="HTML"
                ),
                reply_markup=next_prev_kb
            )

        await state.finish()

@product_router.message(Command('all_products'))
async def all_products_handler(message: Message, state: FSMContext):
    categories = db.get_categories()
    await state.set_state(ShowStates.showCategoryState)
    await message.answer(
        text="Please select a category to view the products.",
        reply_markup=categories_kb_4_products()
    )


@product_router.callback_query(ShowStates.showCategoryState)
async def show_category_callback_query(query: CallbackQuery, state: FSMContext):
    products = db.get_all_products(query.data)
    await state.set_state(ShowStates.showCategoryProductsState)
    await state.update_data(products=products)

    if products:
        count = len(products)
        s = ""
        if count <= 10:
            for i in range(count):
                s += f"<b>{i + 1}.</b> {products[i][1]}\n"
            a = get_next_prev_keyboard(all_count=count, count=count)
        await query.message.edit_text(
            text=s, reply_markup=a, parse_mode="HTML"
        )


@product_router.callback_query(ShowStates.showCategoryProductsState)
async def show_category_callback_query(query: CallbackQuery, state: FSMContext):
    index = int(query.data)
    all_data = await state.get_data()
    products = all_data['products']

    await query.message.answer_photo(
        photo=products[index][3],
        caption=f"<b>{products[index][1]}</b>\n\n<b>{products[index][2]}</b>\n\nPrice: {products[index][4]}\n\nContact: {products[index][-1]}",
        parse_mode="HTML"
    )

    await state.finish()
