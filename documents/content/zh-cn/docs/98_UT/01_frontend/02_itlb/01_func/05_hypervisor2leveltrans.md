---
title: 支持 Hypervisor 扩展与两阶段虚实地址翻译
linkTitle: 05.Hypervisor&2leveltrans
weight: 12
---

在 `RISC-V` 特权指令手册中定义了虚实地址的翻译过程：

1. 设 `a` 为 `satp.ppn` × `PAGESIZE`，并设 `i = LEVELS - 1`。（对于 `Sv48`，`PAGESIZE = 2^{12}`，`LEVELS = 4`）此时，`satp` 寄存器必须处于活动状态，即有效的特权模式必须是 `S` 模式或 `U` 模式。
   
2. 设 `pte` 为地址 `a + va.vpn[i]` × `PTESIZE` 处的 `PTE` 值。（对于 `Sv48`，`PTESIZE = 8`）如果访问 `pte` 违反了 `PMA` 或 `PMP` 检查，则引发与原始访问类型相应的访问错误异常。
   
3. 如果 `pte.v = 0`，或者 `pte.r = 0` 且 `pte.w = 1`，或者 `pte` 中设置了任何为未来标准使用保留的位或编码，则停止并引发与原始访问类型相应的页面错误异常。
   
4. 否则，`PTE` 是有效的。如果 `pte.r = 1` 或 `pte.x = 1`，则转到步骤 5。否则，此 `PTE` 是指向下一级页面表的指针。设 `i = i - 1`。如果 `i < 0`，则停止并引发与原始访问类型相应的页面错误异常。否则，设 `a = pte.ppn` × `PAGESIZE` 并转到步骤 2。
   
5. 找到了叶子 `PTE`。根据当前特权模式和 `mstatus` 寄存器的 `SUM` 和 `MXR` 字段的值，确定请求的内存访问是否被 `pte.r`、`pte.w`、`pte.x` 和 `pte.u` 位允许。如果不允许，则停止并引发与原始访问类型相应的页面错误异常。
   
6. 如果 `i > 0` 且 `pte.ppn[i-1 : 0] = 0`，则这是一个未对齐的大页；停止并引发与原始访问类型相应的页面错误异常。
   
7. 如果 `pte.a = 0`，或者如果原始内存访问是存储且 `pte.d = 0`，则引发与原始访问类型相应的页面错误异常，或者执行以下操作：
   - 如果对 `pte` 的存储将违反 `PMA` 或 `PMP` 检查，则引发与原始访问类型相应的访问错误异常。
   - 以原子方式执行以下步骤：
     - 比较 `pte` 与地址 `a + va.vpn[i]` × `PTESIZE` 处的 `PTE` 值。
     - 如果值匹配，将 `pte.a` 设为 `1`，并且如果原始内存访问是存储，还将 `pte.d` 设为 `1`。
     - 如果比较失败，返回步骤 2。
   
8. 翻译成功。翻译后的物理地址如下：
   - `pa.pgoff = va.pgoff`。
   - 如果 `i > 0`，则这是一个大页翻译，且 `pa.ppn[i - 1 : 0] = va.vpn[i - 1 : 0]`。
   - `pa.ppn[LEVELS - 1 : i] = pte.ppn[LEVELS - 1 : i]`。

在一般的虚实地址翻译过程中，将按照如上所述的过程进行转换，由 satp 寄存器控制进行地址翻译。其中，前端取指通过 `ITLB` 进行地址翻译，后端访存通过 `DTLB` 进行地址翻译。`ITLB` 和 `DTLB` 如果 `miss`，会通过 `Repeater` 向 `L2TLB` 发送请求。在目前设计中，前端取指和后端访存对 `TLB` 均采用非阻塞式访问，即一个请求 `miss` 后，会将请求 `miss` 的信息返回，请求来源调度重新发送 `TLB` 查询请求，直至命中。也就是说，`TLB` 本体是非阻塞的，可以向它连续发送请求，无论结果都可以在下一拍发送任意的请求，但是总体上由于前端的调度，体现为阻塞访问。

在支持了 `H` 扩展的前提下，香山的虚拟化地址翻译过程会经历两个阶段的地址转换，可以将它划分为 `VS` 阶段和 `G` 阶段。`VS` 阶段的地址转换由 `vsatp` 寄存器控制，其实与主机的 `satp` 寄存器非常相似。

![VS 阶段：GVA 至 GPA](GVA-GPA.png)

页表项（`PTE`）的长度为 `64 bit`，也即每个 `4KB` 的页面可以存储 $2^9$ 个 `PTE`。在 `vsatp` 寄存器中存储了第一级页表（即根页表）的物理地址 `PPN`，通过这个 `PPN` 可以找到根页表，并根据 `GVA` 中的 `VPN[3]` 找到对应页表项 `PTE`，在 `PTE` 中存储了指向下一级页表的 `PPN` 以及权限位等。以此方式通过逐级的查找最终达到叶子 `PTE` 并得到 `PPN`，与 `offset` 合成后得到 `GPA`。注意这里的 `GPA` 应当是 `50` 位的，最后一级的 `PPN` 应当是 `38` 位的，这是因为支持 `SV48x4` 的原因，虚拟机的物理地址被拓宽了两位。这样的拓宽并不难实现，只需要在主机分配虚拟机内存空间的时候分配一个 `16KB` 的大页作为根页表即可；通过多使用 `12KB`（本来分配的根页表大小是 `4KB`）的物理内存就可以实现虚拟机地址空间增大四倍。至于页表项能否放下多了两位的 `PPN`，观察 `PTE` 中 `PPN` 的位数为 `44` 位，不需要担心这个问题。`44` 位的 `PPN` 放 `38` 位，前六位并没有清零要求，但是是被忽略的。

![G 阶段：GPA 至 HPA](GPA-HPA.png)

`G` 阶段的地址翻译则不同，由于支持了 `SV48x4`，其根页表被扩展为 `11` 位 `16KB`，因此需要特别注意 `hgatp` 寄存器中存储的 `PPN` 应当对齐 `16KB` 页，在标准情况下 `PPN` 的最后两 `bit` 应当被固定为零，意味着 `hgatp` 寄存器应当指向一个 `16KB` 页的起始地址，以避免根页表在不同的小页面内。

在实际的实现中，地址的翻译并不是这样理想化的先查虚拟机的页表得到 `GPA` 再使用这个 `GPA` 查主机的页表得到 `HPA`。事实上的实现中，我们通过虚拟机的页表查到的下一级页表的物理地址是 `GPA`，并不能通过它访问到下一级页表，每次访问虚拟机的下一级页表都需要进行一次 `GPA` 到 `HPA` 的转换。比如此时给定一个 `GVA`，之后在虚拟机的一级页表（根页表）中根据 `GVA[2]`（`11 bit`）查找得到一个 `PTE`，这个 `PTE` 存储的是二级页表的 `GPA`，得到这个 `GPA` 并不能找到二级页表，因此需要将它转换为 `HPA`，也就是 `G` 阶段的地址翻译。依次查找直到找到最终需要的那个 `HPA`，共需要经历五次 `G` 阶段地址翻译，才能得到最终的 `HPA`。

![香山昆明湖架构 TLB 两阶段地址翻译过程](香山地址翻译过程.png)