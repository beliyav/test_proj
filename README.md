## Запуск API

`docker-compose up`

## Описание технического решения:

**Веб приложение представляет из себя асинхронное приложение на основе aiohttp**

* почему асинхронное? по условиям задачи, API должно иметь высокую производительность, так как основные временные затраты будут на IO, то была выбрана асинхронная схема
* почему aiohttp? на мой взгляд это один из максимаьно минималистичных/чистых HTTP серверов (асинхронных). На самом деле вариантов было много, хоть bottle + gevent/eventlet
* я осознанно не выбирал какие-то фреймворки, т.к. нет требований к авторизации/сессиям/шаблонам + это все влияет на производительность


**В качестве системы хранения выбрана PostgreSQL**
* я с ней больше всего работал + она полность удовлетворяет требованиям ACID, которые для платежных данных обязаны быть
* в качестве библиотеки для работы с PostgreSQL была выбрана asyncpg, пока что это самая производительная библиотека, которую я знаю
* я осознанно не использую ORM, т.к. в данном случае нет сложной бизнес-логики или вероятности ее появления + это влияет на производительность
* для миграций выбрана маленькая библиотека YoYo. Да, в данный момент миграции не нужны, но на мой взгляд это очень дешевое вложение в самом начале, которое заметно облегчит жизнь в тот момент если они понадобятся

**В качестве библиотеки валидации выбрана cerberus, просто потому что она простая и понятная**


## Структура API

### Обьекты:

**Кошельки/счета** - `Accounts{id: int, email: string, balance: decimal, ctime: ISO Timestamp UTC}`
* поле еmail символизирует клиента


**Транзакции** - `Transactions{id: int, source_account_id: int, target_transaction_id: int, amount: decimal, ctime: ISO Timestamp UTC}`
* source_account_id может быть Null, это значит что было пополнение со стороны владельца кошелька


### Эндпоинты:

**POST /account - создание кошелька**
<pre>
    {
        email: str
    }
</pre>


**GET /account/{id} - получение структуры кошелька**


**POST /account/{id}/payment - зачисление денег на счет**
<pre>
    {
        amount: decimal
    }
</pre>

**POST /transaction - создание перевода с одного кошелька на другой**
<pre>
    {
        source_account_id: int,
        target_account_id: int,
        amount: decimal
    }
</pre>
* Да, поплнение кошелька можно было тоже сделать через транзакции, но я решил логически разделить эти операции.


**GET /transaction/{id} - получение структуры транзакции**


## Нюансы работы:

**Максимальная сумма на счету 999 999.99. Все округляется до тысячных. Для хранения денег использутся Decimal в Python и Numeric(8,2) в PostgreSQL**

**Для хранения текущего баланса у каждого кошелька есть поле balance, которое пересчитывается при каждой операции.**

* Это можно было сделать хранимкой + триггер на стороне базы, но я не сторонник размазывая логики по нескольким компонентам, если для этого нет предпосылок (например проблем с перфомансом)
* Это можно было сделать суммой всех транзакций на этот кошелек - сумма всех транзакций с этого кошелька и каждый раз ее пересчитывать, что будет долго + чем дольше истема будет существовать тем это будет дольше

**Для проведения транзакций выбран паттерн Pessimistic Locking - я явно лочу счета, которые участвуют в транзакции.**
* Нет информации о реальных кейсах для этой системы, поэтому я предполагаю любые кейсы
* Консистентность данных важнее скорости
* На мой взгляд алгоритм с Optimistic Locking выглядит более сложным для данного кейса.

**Как я борюсь с возможными дедлоками?**

В данном случае никак! Дедлок заметит база и оборвет транзакцию. При этом консистентность данных не будет нарушена. иногда лучше отдать пользователю сообщение "повторите запрос позже".

Понятно что в production-ready решении этому вопросы было бы уделено больше внимания, вот пара примеров, как бы я подходил к решению этих проблем:
* можно было делать очередь для запросов, что бы все запросы к базе выполнялись в порядке строгой очереди, но тогда были бы вопросы с масштабируемостью
* 1 пункт можно дополнить тем, что только некоторые запросы попадпли бы в очередь (например если есть вероятность дедлока с текущими транзакциями), остальные выполнялись бы паралельно
* использовать асинхронные подход в api, например мы создаем обьект транзакции и потом опрашиваем его успешность. Бэкенд в это время сам следить за выполнением этот транзакции (например ретраит при ошибке)


## Тесты
Тесты написаны, но не автоматизированы, для их запуска надо: 
1) поднять PostgreSQL
2) накатить на него миграции
3) создать venv
4) сделать pip install -e . для этого проекта в венве
5) запустить pytest -vs tests/





