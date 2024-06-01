Преподаватели, Пенской Александр Владимирович.

forth | stack | neum | mc -> hw | instr | struct | stream | mem | cstr | prob2 | cache

Упрощенный вариант

## Язык программирования

``` ebnf
program ::= procedure_def | calling_procedure| loop|while|special_func

procedure_def ::= : procedure_name 
                "[" basic_command basic_command "]"|
                "[" previously_defined_procedure  previously_defined_procedure"]"
                ;
special_func ::= : WRITE "literal" ;          
                
calling_procedure ::=  procedure_name ;     

basic_command :: = read|print|halt|write

loop :: = LOOP previously_defined_procedure iterations ;

while :: = WHILE condition previously_defined_procedure ;
1-true
0-false
$number-special variable for referencing value in memory

IF ::= IF condition previously_defined_procedure ;

iterations Должно быть натуральным числом.

Код выполняется последовательно. Операции:
    
Команды,как и названия функций, чувствительны к регистру. 
    
Команды содержат только прописные буквы. 

Названия процедур содержат только строчные буквы.

Если есть несколько определений одной и той же процедуры,то будет взято последние.

Память выделяется статически, при запуске модели. Видимость данных -- глобальная. Поддержка литералов Присутсвует.

Название процедуры не может начинаться с числа.
          
Система команд

Машинное слово - 32 бита,знаковое.

SUM- специальное слово для суммирования.
 
Доступ к памяти осуществляется по адресу, хранящемуся в специальном регистре DR. Установка адреса осуществляется путём инкрементирования или декрементирования инструкциями < и >.

### Набор инструкций

| Язык | Инструкция   | Кол-во тактов | Описание                                                    |
|:-----|:-------------|:--------------|:------------------------------------------------------------|
|read_mem_to_stack| read_mem     | 1        | Чтение данных из  памяти. (*DR)->(stack_top)                                              |
|read_io_to_stack| read_io      | 1          | Чтение данных из  IO. (*IO)->(stack_top)                                              |
| print | print    | 1             | Вывод данных. (POP STACK)->out                                                |
| halt  | halt     | 0             | остановка                                                   |
| write_mem_from_stack| write    | 1          | Запись данных в память по адрессу DR с верхушки стека. DATA->(*DR)                                      |
| write_mem_from_IO   | write    | 1           | Запись данных в память в порт IO из inner_buffer. DATA->(*IO)                                      |
| inc   | increment| 1             | DR+1->DR
| dec   | decrement| 1             | DR-1 ->DR     
| write_literal_into_memory|write_literal_into_memory | Запись строки в память по адресу DR,DR-1 и тд.              
| sum |sum| Сложить два числа.  
|sum_all|sum_all| Складывает все числа на стеке и возвращает результат в память.
|restore|restore| Restore initial value of Memory register.            

```