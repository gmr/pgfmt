---
layout: default
author: mattmc3
title: Modern SQL Style Guide
revision: 2019-01-17
version: 1.0.1
description: A guide to writing clean, clear, and consistent SQL.
---

# Modern SQL Style Guide

```sql
select *
  from modern.sql_style_guide as guide
 where guide.attributes in ('clean', 'clear', 'consistent')
   and guide.look = 'beautiful'
```

## Purpose

These guidelines are designed to make SQL statements easy to write, easy to
read, easy to maintain, and beautiful to see. This document is to be used as a
guide for anyone who would like to codify a team's preferred SQL style.

This guide is opinionated in some areas and relaxed in others. You can use this
set of guidelines, fork them, or make your own - the key here is that you pick a
style and stick to it. The odds of making everyone happy are low, so compromise
is a guiding principle to achieve cohesion.

It is easy to include this guide in Markdown format as a part of a project's
code base or reference it here for anyone on the project to freely read.

This guide is based on various existing attempts at SQL standards including:
[http://www.sqlstyle.guide][sqlstyleguide] and
[Kickstarter guide][kickstarter-sql-guide]. Due to its origins, it is
licensed under a [Creative Commons Attribution-ShareAlike 4.0 International
License][license].

The example SQL statements used are based on tables in the
[AdventureWorks][adventureworks] database. Note that due to the use of the
existing AdventureWorks schema, some of the guidelines in this document
are not always followed, especially with regards to naming conventions.
Those discrepancies will be called out as they appear.

**NOTE**: This style guide is written for use with [Microsoft SQL
Server][mssql], but much of it can be applied to any SQL database with some
simple modifications.

## Principles

* We take a disciplined and practical approach to writing code.
* We treat SQL like any other source code, which should be checked into
  source control, peer reviewed, and properly maintained.
* We believe consistency in style is important, and we value craftsmanship, but
  not to the exclusion of other practical concerns.
* We demonstrate intent explicitly in code, via clear structure and comments
  where needed.
* We adhere to a consistent style for handwritten SQL so that our code can
  thrive in an environment with many authors, editors, and readers.

## Quick look

Before getting into all the specifics, here is a quick look at some examples
showing well formatted, beautiful SQL that matches the recommendations in
this style guide:

```sql
-- basic select example
select p.Name as ProductName
     , p.ProductNumber
     , pm.Name as ProductModelName
     , p.Color
     , p.ListPrice
  from Production.Product as p
  join Production.ProductModel as pm
    on p.ProductModelID = pm.ProductModelID
 where p.Color in ('Blue', 'Red')
   and p.ListPrice < 800.00
   and pm.Name like '%frame%'
 order by p.Name
```

```sql
-- basic insert example
insert into Sales.Currency (CurrencyCode, Name, ModifiedDate)
values ('XBT', 'Bitcoin', getutcdate())
     , ('ETH', 'Ethereum', getutcdate())
```

```sql
-- basic update example
update p
   set p.ListPrice = p.ListPrice * 1.05
     , p.ModifiedDate = getutcdate()
  from Production.Product as p
 where p.SellEndDate is null
   and p.SellStartDate is not null
```

```sql
-- basic delete example
delete cc
  from Sales.CreditCard as cc
 where cc.ExpYear < '2003'
   and cc.ModifiedDate < dateadd(year, -1, getutcdate())
```

## Rules

### General guidance

* Favor using a ["river"][rivers] for vertical alignment so that a query can be
  quickly and easily be scanned by a new reader.
* Comments should appear at the top of your query or script, and should explain
  the intent of the query, not the mechanics.
* Try to comment things that aren't obvious about the query (e.g., why a
  particular filter is necessary, why an optimization trick was needed, etc.)
* Favor being descriptive over terseness:

  __GOOD__:
  `select emp.LoginID as EmployeeUserName`

  __BAD__:
  `select emp.LoginID as EmpUsrNm`

* Follow any existing style in the script before applying this style guide.
  The SQL script should have one clear style, and these rules should not be
  applied to existing scripts unless the whole script is being changed to
  adhere to the same style.
* Favor storing `datetime` and `datetime2` in UTC unless embedding timezone
  information (`datetimeoffset`) so that times are clear and convertible.
  Use [ISO-8601][iso-8601] compliant time and date information
  (`YYYY-MM-DD HH:MM:SS.SSSSS`) when referring to date/time data.

### Casing

Do not SHOUTCASE or "Sentence case" SQL keywords (e.g., prefer `select`, not
`SELECT` or `Select`). SHOUTCASED SQL is an anachronism, and is not appropriate
for modern SQL development. Using lowercase keywords is preferred because:

* UPPERCASE words are harder to type and
  [harder to read][shoutcase-typeography].
* SQL syntax is not case-sensitive, and thus lowercase keywords work correctly
  in all variants of SQL
* No other modern languages use ALLCAPS keywords.
* Modern editors color code SQL keywords, so there is not a need to distinguish
  keywords by casing.
* If you are in an environment where your keywords are not colored (i.e. as a
  string in another language), using a river for formatting provides a similar
  benefit of highlighting important keywords without resorting to CAPS.
* UPPERCASE IS ASSOCIATED WITH SHOUTING WHEN SEEN IN TEXT, IS HARD TO READ, AND
  MAKES SQL FEEL MORE LIKE COBOL THAN A MODERN LANGUAGE.

If the SQL script you are editing already uses SHOUTCASE keywords, match that
style or change *all* keywords to lowercase. Favor bending the rules for the
sake of consistency rather than mixing styles.

### Naming guidance

* Names should be `underscore_separated` or `PascalCase` but do not mix styles.

  __GOOD__:
  `select count(*) as the_tally, sum(*) as the_total ...`

  __BAD__:
  `select count(*) as The_Tally, sum(*) as theTotal ...`

#### Tables

* Do not use [reserved words][sql-server-keywords] for table names if possible.
* Prefer the shortest commonly understood words to name a table.
* Naming a table as a plural makes the table easier to speak about. (e.g.
  favor `employees` over `employee`)
* Do not use object prefixes or Hungarian notation (e.g. `sp_`, `prc_`, `vw_`,
  `tbl_`, `t_`, `fn_`, etc).
* Tables with semantic prefixes are okay if they aid understanding the nature
  of a table (e.g. in a Data Warehouse where it is common to use prefixes like
  `Dim` and `Fact`).
* Avoid giving a table the same name as one of its columns.
* Use a joining word for many-to-many joining tables (cross references) rather
  than concatenating table names (e.g. `Xref`):

  __GOOD__:
  `drivers_xref_cars`

  __BAD__:
  `drivers_cars`

* Tables should always have a primary key. A single column, auto-number
  (identity) surrogate key is preferable.
* Natural keys or composite keys can be enforced with unique constraints in
  lieu of making them a primary key.
* Composite keys make for verbose and slow foreign key joins. `int`/`bigint`
  primary keys are optimal as foreign keys when a table gets large.
* Tables should always have `created_at` and `updated_at` metadata fields in
  them to make data movement between systems easier (ETL). Also, consider
  storing deleted records in archival tables, or having a `deleted_at` field for
  soft deletes.
* Don't forget the needs of data analysts and ETL developers when designing your
  model.

#### Columns

* Do not use [reserved words][sql-server-keywords] for column names if possible.
* Prefer not simply using `id` as the name of the primary identifier for the
  table if possible.
* Do not add a column with the same name as its table and vice versa.
* Avoid common words like `Name`, `Description`, etc. Prefer a descriptive
  prefix for those words so that they don't require aliases when joined to other
  tables with similarly named columns. (**NOTE:** _This guide uses
  the AdventureWorks database, which commonly has columns named `Name` against
  this guide's advice. Remember that an existing convention may be in place that
  is beyond your control._ )
* Do not use `Desc` as an abbreviation for `Description`. Spell it out, or use
  some other non-keyword.

#### Aliases

* Aliases should relate in some way to the object or expression they are aliasing.
* As a rule of thumb the alias can be the first letter of each word in the object's
  name or a good abbreviation.
* If there is already an alias with the same name then append a number.
* When using a subquery, prefix aliases with an `_` to differentiate them from
  aliases in the outer query.
* Always include the `as` keyword. It makes the query easier to read and is
  explicit.
* For computed data (i.e. `sum()` or `avg()`) use the name you would give it were
  it a column defined in the schema.

### Whitespace

* No tabs. Use spaces for indents.
* Configure your editor to 4 spaces per indent, but prefer your SQL to indent
  to the "river", and not to a set indent increment.
* No trailing whitespace.
* No more than two blank lines between statements.
* No empty lines in the middle of a single statement.
* One final newline at the end of a file
* Use an [.editorConfig file][editor-config] to enforce reasonable whitespace
  rules if your SQL editor supports it:

```ini
# .editorConfig is awesome: https://EditorConfig.org

# SQL files
[*.{sql,tsql,ddl}]
charset = utf-8
indent_style = space
indent_size = 4
end_of_line = crlf
trim_trailing_whitespace = true
insert_final_newline = true
```

### River formatting

Spaces may be used to line up the code so that the root keywords all end on the
same character boundary. This forms a "river" down the middle making it easy for
the reader's eye to scan over the code and separate the keywords from the
implementation detail. Rivers are [bad in typography][rivers], but helpful here.
[Celko's book][celko] describes using a river to vertically align your query.
Right align keywords to the river if you chose to use one. The `on` clause in
the `from` may have its own river to help align information vertically.
Subqueries should create their own river as well.

```sql
-- a river in the 7th column helps vertical readability
select prdct.Name as ProductName
     , prdct.ListPrice
     , prdct.Color
     , cat.Name as CategoryName
     , subcat.Name as SubcategoryName
  from Production.Product as prdct
  left join Production.ProductSubcategory as subcat
    on prdct.ProductSubcategoryID = subcat.ProductSubcategoryID
  left join Production.ProductCategory as cat
    on subcat.ProductCategoryID = cat.ProductCategoryID
 where prdct.ListPrice <= 1000.00
   and prdct.ProductID not in (
           select _pd.ProductID
             from Production.ProductDocument _pd
            where _pd.ModifiedDate < dateadd(year, -1, getutcdate())
       )
   and prdct.Color in ('Black', 'Red', 'Silver')
 order by prdct.ListPrice desc, prdct.Name
```

```sql
-- alternately, a river in the a different column is fine if that is preferred
-- due to longer keywords, but know that indenting can feel "off" if the
-- `select` is not in the first column for the query
   select prdct.Name as ProductName
        , prdct.ListPrice
        , prdct.Color
        , cat.Name as CategoryName
        , subcat.Name as SubcategoryName
     from Production.Product as prdct
left join Production.ProductSubcategory as subcat
       on prdct.ProductSubcategoryID = subcat.ProductSubcategoryID
left join Production.ProductCategory as cat
       on subcat.ProductCategoryID = cat.ProductCategoryID
    where prdct.ListPrice <= 1000.00
      and prdct.ProductID not in (
              select _pd.ProductID
                from Production.ProductDocument _pd
               where _pd.ModifiedDate < dateadd(year, -1, getutcdate())
          )
      and prdct.Color in ('Black', 'Red', 'Silver')
 order by prdct.ListPrice desc, prdct.Name
```

### Indent formatting

Using a river can be tedious, so if this alignment is not preferred by your
team, then a standard 4 space indent can be used in place of a river.

Major keywords starting a clause should occupying their own line. Major keywords
are:

* Select statement
  * `select`
  * `into`
  * `from`
  * `where`
  * `group by`
  * `having`
  * `order by`
* Insert statement additions
  * `insert into`
  * `values`
* Update statement additions
  * `update`
  * `set`
* Delete statement additions
  * `delete`

All other keywords are minor and should appear after the indent and not
occupy a line to themselves. Other than this section, this guide will stick to
showing "river" formatting examples.

```sql
-- Editors tend to handle indenting style better than river alignment. River
-- formatting has advantages over indent formatting, but this style is
-- acceptable.
select
    prdct.Name as ProductName
    ,prdct.ListPrice
    ,prdct.Color
    ,cat.Name as CategoryName
    ,subcat.Name as SubcategoryName
from
    Production.Product as prdct
    left join Production.ProductSubcategory as subcat
        on prdct.ProductSubcategoryID = subcat.ProductSubcategoryID
    left join Production.ProductCategory as cat
        on subcat.ProductCategoryID = cat.ProductCategoryID
where
    prdct.ListPrice <= 1000.00
    and prdct.Color in ('Black', 'Red', 'Silver')
order by
    prdct.ListPrice desc, prdct.Name
```

### `select` clause

Select the first column on the same line, and align all subsequent columns
after the first get their own line.

```sql
select prdct.Color
     , cat.Name as CategoryName
     , count(*) as ProductCount
  from ...
```

If three or fewer columns are selected, have short names, and don't need
aliased, you may chose to have them occupy the same line for brevity.

```sql
-- shortcut for small columns
select p.Color, c.Name, p.ListPrice
  from ...
```

If using a `select` modifier like `distinct` or `top`, put the first column
on its own line.

```sql
-- treat the first column differently when using distinct and top
select distinct
       p.Color
     , c.Name as CategoryName
  from ...
```

Use commas as a prefix as opposed to a suffix. This is preferred because:

* It makes it easy to add new columns to the end of the column list, which is
  more common than at the beginning
* It prevents unintentional aliasing bugs (missing comma)
* It makes commenting out columns at the end easier
* When statements take multiple lines like windowing functions and `case`
  statements, the prefix comma makes it clear when a new column starts
* It does not adversely affect readability

The comma should border the "river" on the keyword side.

__GOOD__:

```sql
select Name
     , ListPrice
     , Color
     , CategoryName
   ...
```

__BAD__:

```sql
-- whoops! forgot a trailing comma because it's hard to see, making an
-- accidental alias of `ListPrice Color`
select Name,
       ListPrice
       Color,
       CategoryName
   ...
```

Always use `as` to rename columns. `as` statements can be used for additional
vertical alignment but don't have to be:

__GOOD__:

```sql
select prdct.Color as ProductColor
     , cat.Name    as CategoryName
     , count(*)    as ProductCount
  from ...
...
```

__BAD__:

```sql
select prdct.Color ProductColor
     , cat.Name CategoryName
     , count(*) ProductCount
  from ...
...
```

Always rename aggregates, derived columns (e.g. `case` statements), and
function-wrapped columns:

```sql
select ProductName
     , sum(UnitPrice * OrderQty) as TotalCost
     , getutcdate() as NowUTC
  from ...
```

Always use table alias prefixes for all columns when querying from more than one
table. Single character aliases are fine for a few tables, but are less likely
to be clear as a query grows:

```sql
select prdct.Color
     , subcat.Name as SubcategoryName
     , count(*) as ItemCount
  from Production.Product as prdct
  left join Production.ProductSubcategory as subcat
    on ...
```

Do not bracket-escape table or column names unless the names contain keyword
collisions or would cause a syntax error without properly qualifying them.

__GOOD__:

```sql
-- owner and status are keywords
select Title
     , [Owner]
     , [Status]
from Production.Document
```

__BAD__:

```sql
-- extra brackets are messy and unnecessary
select [Title]
     , [Owner]
     , [Status]
from [Production].[Document]
```

#### Windowing functions

Long Window functions should be split across multiple lines: one for each
clause, aligned with a river. Partition keys can share the same line, or be
split. Ascending order is an intuitive default and thus using an explicit `asc`
is not necessary whereas `desc` is. All window functions should be aliased.

```sql
select p.ProductID
     , p.Name as ProductName
     , p.ProductNumber
     , p.ProductLine
     , row_number() over (partition by p.ProductLine
                                     , left(p.ProductNumber, 2)
                              order by right(p.ProductNumber, 4) desc) as SequenceNum
     , p.Color
  from Production.Product p
 order by p.ProductLine
     , left(p.ProductNumber, 2)
     , SequenceNum
```

#### `case` statements

`case` statements aren't always easy to format but try to align `when`, `then`,
and `else` together inside `case` and `end`.

`then` can stay on the `when` line if needed, but aligning with `else` is
preferable.

```sql
select dep.Name as DepartmentName
     , case when dep.Name in ('Engineering', 'Tool Design', 'Information Services')
            then 'Information Technology'
            else dep.GroupName
       end as NewGroupName
  from HumanResources.Department as dep
 order by NewGroupName, DepartmentName
```

### `from` clause

Only one table should be in the `from` part. Never use comma separated
`from`-joins:

__GOOD__:

```sql
select cust.AccountNumber
     , sto.Name as StoreName
  from Sales.Customer as cust
  join Sales.Store as sto
    on cust.StoreID = sto.BusinessEntityID
...
```

__BAD__:

```sql
select cust.AccountNumber
     , sto.Name as StoreName
  from Sales.Customer as cust, Sales.Store as sto
 where cust.StoreID = sto.BusinessEntityID
...
```

Favor not using the extraneous words `inner` or `outer` when joining tables.
Alignment is easier without them, they don't add to the understanding of the
query, and the full table list is easier to scan without excessive staggering:

__GOOD__:

```sql
-- this is easier to format and read
   select *
     from HumanResources.Employee as emp
     join Person.Person as per
       on emp.BusinessEntityID = per.BusinessEntityID
left join HumanResources.EmployeeDepartmentHistory as edh
       on emp.BusinessEntityID = edh.BusinessEntityID
left join HumanResources.Department as dep
       on edh.DepartmentID = dep.DepartmentID
```

__BAD__:

```sql
-- verbosity for the sake of verbosity is not helpful
-- `join` by itself always means `inner join`
-- `outer` is an unnecessary optional keyword
         select *
           from HumanResources.Employee as emp
     inner join Person.Person as per
             on emp.BusinessEntityID = per.BusinessEntityID
left outer join HumanResources.EmployeeDepartmentHistory as edh
             on emp.BusinessEntityID = edh.BusinessEntityID
left outer join HumanResources.Department as dep
             on edh.DepartmentID = dep.DepartmentID
```

The `on` keyword and condition can go on its own line, but is easier to scan if
it lines up on the `join` line. This is an acceptable style alternative:

```sql
-- this is an easier format to scan visually, but comes at the cost of longer
-- lines of code.
   select *
     from HumanResources.Employee as emp
     join Person.Person as per                            on emp.BusinessEntityID = per.BusinessEntityID
left join HumanResources.EmployeeDepartmentHistory as edh on emp.BusinessEntityID = edh.BusinessEntityID
left join HumanResources.Department as dep                on edh.DepartmentID = dep.DepartmentID
...
```

Additional filters in the `join` go on new indented lines. Line up using the
`on` keyword:

__GOOD__:

```sql
   select emp.JobTitle
     from HumanResources.Employee as emp
left join HumanResources.EmployeeDepartmentHistory as edh
       on emp.BusinessEntityID = edh.BusinessEntityID
left join HumanResources.Department as dep
       on edh.DepartmentID = dep.DepartmentID
      and dep.Name <> dep.GroupName  -- multi-conditions start a new line
    where dep.DepartmentID is null
```

__BAD__:

```sql
   select emp.JobTitle
     from HumanResources.Employee as emp
left join HumanResources.EmployeeDepartmentHistory as edh
       on emp.BusinessEntityID = edh.BusinessEntityID
left join HumanResources.Department as dep
       on edh.DepartmentID = dep.DepartmentID and dep.Name <> dep.GroupName  -- needs a new line
    where dep.DepartmentID is null
```

Begin with `inner join`s and then list `left join`s, order them semantically,
and do not intermingle `left join`s with `inner join`s unless necessary. Order
the `on` clause with joining aliases referencing tables top-to-bottom:

__GOOD__:

```sql
select *
  from Production.Product as prd
  join Production.ProductModel as prm
    on prd.ProductModelID = prm.ProductModelID
  left join Production.ProductSubcategory as psc
    on prd.ProductSubcategoryID = psc.ProductSubcategoryID
  left join Production.ProductDocument as doc
    on prd.ProductID = doc.ProductID
```

__BAD__:

```sql
select *
  from Production.Product as prd
  left join Production.ProductSubcategory as psc
    on psc.ProductSubcategoryID = prd.ProductSubcategoryID  -- backwards
  join Production.ProductModel as prm                       -- intermingled
    on prm.ProductModelID = prd.ProductModelID              -- backwards
  left join Production.ProductDocument as doc
    on prd.ProductID = doc.ProductID
```

Avoid `right joins` as they are usually better written with a `left join`

__GOOD__:

```sql
select *
  from Production.Product as prd
  left join Production.ProductSubcategory as psc
    on ...
```

__BAD__:

```sql
select *
  from Production.ProductSubcategory as psc
 right join Production.Product as prd
    on ...
```

### `where` clause

Multiple `where` clauses should go on different lines and align to the river:

```sql
select *
  from Production.Product prd
 where prd.Weight > 2.5
   and prd.ListPrice < 1500.00
   and Color in ('Blue', 'Black', 'Red')
   and SellStartDate >= '2006-01-01'
...
```

When mixing `and` and `or` statements, do not rely on order of operations and
instead always use parenthesis to make the intent clear:

```sql
select *
  from Production.Product prd
 where (prd.Weight > 10.0
   and Color in ('Red', 'Silver'))
    or Color is null
```

Always put a semicolon on its own line when using them. This prevents common
errors like adding conditions to a `where` clause and neglecting to move the
trailing semicolon:

__GOOD__:

```sql
-- The prefix semicolon is clear and easy to spot when adding to a `where`
delete prd
  from Production.Product prd
 where prd.ListPrice = 0
   and weight is null
   and size is null
;
...
```

__BAD__:

```sql
-- A trailing semicolon is sinister.
-- We added some where conditions and missed it.
-- This is a destructive bug.
delete prd
  from Production.Product prd
 where prd.ListPrice = 0;  -- dangerous
   and weight is null      -- syntax error here, but the bad delete is valid
   and size is null
...
```

### `group by` clause

Maintain the same column order as the `select` clause in the `group by`:

__GOOD__:

```sql
  select poh.EmployeeID
       , poh.VendorID
       , count(*) as OrderCount
       , avg(poh.SubTotal) as AvgSubTotal
    from Purchasing.PurchaseOrderHeader as poh
group by poh.EmployeeID
       , poh.VendorID
```

__BAD__:

```sql
-- messing with the 'group by' order makes it hard to scan for accuracy
  select poh.EmployeeID
       , poh.VendorID
       , count(*) as OrderCount
       , avg(poh.SubTotal) as AvgSubTotal
    from Purchasing.PurchaseOrderHeader as poh
group by poh.VendorID  -- out of order
       , poh.EmployeeID
```

### `having` clause

A `having` clause is just a `where` clause for aggregate functions. The same
rules for `where` clauses apply to `having`.

__Example__:

```sql
  select poh.EmployeeID
       , poh.VendorID
       , count(*) as OrderCount
       , avg(poh.SubTotal) as AvgSubTotal
    from Purchasing.PurchaseOrderHeader as poh
group by poh.EmployeeID
       , poh.VendorID
  having count(*) > 1
     and avg(poh.SubTotal) > 3000.00
```

### `order by` clause

Do not use the superfluous `asc` in `order by` statements:

__GOOD__:

```sql
-- asc is implied and obvious
  select per.LastName
       , per.FirstName
    from Person.Person per
order by per.LastName
       , per.FirstName
```

__BAD__:

```sql
-- asc is clutter - it's never ambiguous when you wanted to sort ascending
  select per.LastName
       , per.FirstName
    from Person.Person per
order by per.LastName asc  -- useless asc
       , per.FirstName asc
```

Ordering by column number is okay, but not preferred:

```sql
-- This is okay, but not great.
  select per.FirstName + ' ' + per.LastName as FullName
       , per.LastName + ', ' + per.FirstName as LastFirst
    from Person.Person per
order by 2
```

The `by` keyword can sit on the other side of a 7th column river, but align
the order by columns:

```sql
select per.FirstName
     , per.LastName
  from Person.Person per
 order by per.LastName
        , per.FirstName
```

If three or fewer columns are in the `order by` and have short names you may
chose to have them occupy the same line for brevity.

```sql
-- shortcut for small columns
select per.FirstName, per.LastName
  from Person.Person per
 order by per.LastName, per.FirstName
```

[kickstarter-sql-guide]: https://gist.github.com/fredbenenson/7bb92718e19138c20591#file-kickstarter_sql_style_guide-md
[sqlstyleguide]: http://www.sqlstyle.guide
    "SQL style guide by Simon Holywell"
[adventureworks]: https://docs.microsoft.com/en-us/sql/samples/adventureworks-install-configure
    "AdventureWorks sample database"
[shoutcase-typeography]: https://practicaltypography.com/all-caps.html
[editor-config]: https://EditorConfig.org
[mssql]: https://www.microsoft.com/en-us/sql-server/default.aspx
    "Microsoft SQL Server"
[simon]: https://www.simonholywell.com/?utm_source=sqlstyle.guide&utm_medium=link&utm_campaign=md-document
    "SimonHolywell.com"
[celko]: https://www.amazon.com/gp/product/0120887975/ref=as_li_ss_tl?ie=UTF8&linkCode=ll1&tag=treffynnon-20&linkId=9c88eac8cd420e979675c815771313d5
    "Joe Celko's SQL Programming Style (The Morgan Kaufmann Series in Data Management Systems)"
[iso-8601]: https://en.wikipedia.org/wiki/ISO_8601
    "Wikipedia: ISO 8601"
[rivers]: http://practicaltypography.com/one-space-between-sentences.html
    "Practical Typography: one space between sentences"
[reserved-keywords]: #reserved-keyword-reference
    "Reserved keyword reference"
[license]: http://creativecommons.org/licenses/by-sa/4.0/
    "Creative Commons Attribution-ShareAlike 4.0 International License"
[sql-server-keywords]: https://docs.microsoft.com/en-us/sql/t-sql/language-elements/reserved-keywords-transact-sql
    "SQL Server reserved keywords"
