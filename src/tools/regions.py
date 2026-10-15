"""地区（国家 → 省 → 市 → 区）的**查询层**。

数据在 `tools/regions_data.py`（**生成的**，见 `scripts/gen_regions.py`）：
`COUNTRIES` 国家表、`CHINA` 中国三级、`WORLD` 已收录的各国一级行政区。
这一层只回答三件事，页面不用自己拼树、也不用管数据长什么样：

- `children(path)`：`path` 下面还有哪些（给空元组就说明**到头了**，点一下就该把
  `label(path)` 当成选中的地区）；
- `label(path)`：把一串路径拼成给用户看的「中国 上海市 浦东新区」；
- `match_location(...)`：把定位拿到的几个名字（往往**是简写**：「上海」「浦东新」）
  落回树上的某一串，落不上给 `None`。

⚠️ 老数据里 `region` 可能就是「杭州」这种自由文本（这一页以前是个输入框），
所以对不上树的值**原样显示**即可，别在这里报错。
"""

from collections.abc import Iterable, Sequence

from tools.regions_data import CHINA, COUNTRIES, WORLD

# 中国在这棵树里的名字（`CHINA` 就是挂在它下面的）。
CHINA_NAME = "中国"


def children(path: Sequence[str]) -> tuple[str, ...]:
    """`path` 的下一级；`path` 已经是叶子就给空元组。"""
    if not path:
        return COUNTRIES
    country = path[0]
    if country != CHINA_NAME:
        # 其他国家：只收录了一级行政区，再往下没有了。
        regions = WORLD.get(country) or ()
        return regions if len(path) == 1 else ()
    if len(path) == 1:
        return tuple(CHINA)
    cities = CHINA.get(path[1])
    if cities is None:
        return ()
    if len(path) == 2:
        return _under_province(path[1], cities)
    # 第三段是市（或直辖市的区县那一层）：区县已经到头。
    return ()


def label(path: Sequence[str]) -> str:
    """这一串显示成「中国 上海市 浦东新区」（照小红书那版：空格分隔）。"""
    return " ".join(part for part in path if part)


def _under_province(province: str, cities: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    """省级下面那一层。

    ⚠️ 直辖市（北京 / 上海 / 天津 / 重庆）与港澳台在数据里是**自己套自己**一层
    （`{"上海市": ("浦东新区", ...)}`）—— 那一层「市」对用户没意义，这里直接拆掉，
    于是「中国 → 上海市 → 浦东新区」正好三段，和定位给的那行对得上。
    """
    if len(cities) == 1 and province in cities:
        return cities[province]
    return tuple(cities)


def _is_flat(province: str, cities: dict[str, tuple[str, ...]]) -> bool:
    """省级下面是不是「自己套自己」（直辖市 / 港澳台，见 `_under_province`）。"""
    return len(cities) == 1 and province in cities


# ---------------------- 定位结果 → 树上的路径 ----------------------


def _pick(name: str, options: Iterable[str]) -> str | None:
    """在 `options` 里给 `name` 找一个最像的：**全等 → 前缀 → 包含**，都中了取最短的。

    定位接口给的常是简写：「上海」→「上海市」、「浦东新」→「浦东新区」、
    「广西」→「广西壮族自治区」。取最短的那个是为了别让「内蒙古」这种短名
    被更长的候选挤掉。
    """
    name = (name or "").strip()
    if not name:
        return None
    candidates: list[tuple[int, int, str]] = []
    for option in options:
        if option == name:
            candidates.append((0, len(option), option))
        elif option.startswith(name) or name.startswith(option):
            candidates.append((1, len(option), option))
        elif name in option or option in name:
            candidates.append((2, len(option), option))
    if not candidates:
        return None
    return min(candidates)[2]


def match_location(
    *,
    country: str = "",
    province: str = "",
    city: str = "",
    district: str = "",
) -> tuple[str, ...] | None:
    """把定位拿到的几个名字落到树上；一个都认不出给 `None`。

    各级名字都是**可有可无**的（不同接口给的粒度不一样），所以每一段都往下试一层，
    能在哪一层停下就停在哪一层 —— 只要认出了国家 / 省，就有一串能显示的值。
    """
    if not (country or province or city):
        return None

    found_country = _pick(country, COUNTRIES)
    if found_country and found_country != CHINA_NAME:
        # 其他国家：认得出一级行政区就到那一级，认不出就只到国家。
        region = _pick(province or city, WORLD.get(found_country) or ())
        return (found_country, region) if region else (found_country,)

    # 国家认不出来时也当中国 —— 定位接口给的省市绝大多数都在国内，
    # 而国家名在英文接口里可能是「China」之类，`_pick` 认不出来（见 tools/location.py）。
    level = [CHINA_NAME]
    # 港澳台的省级单位有时是**从国家名那一段**给出来的（IP 定位把「香港」当国家报），
    # 所以国家名也拿来对一下省级。
    province_hit = (
        _pick(province, CHINA) or _pick(city, CHINA) or _pick(country, CHINA)
    )
    if not province_hit:
        # 只给了市名（「杭州」）：去各省下面找一找，找到就连省一起给出来。
        for name, cities in CHINA.items():
            hit = _pick(city or province, tuple(cities))
            if hit:
                return (CHINA_NAME, name, hit)
        return tuple(level)
    level.append(province_hit)
    cities = CHINA[province_hit]
    if _is_flat(province_hit, cities):
        # 直辖市 / 港澳台：这一段名字本来就是省级，下一层直接是区。
        hit = _pick(district or city or province, cities[province_hit])
    else:
        city_hit = _pick(city, cities) or _pick(district, cities)
        if not city_hit:
            return tuple(level)
        level.append(city_hit)
        hit = _pick(district, cities[city_hit])
    return (*level, hit) if hit else tuple(level)
